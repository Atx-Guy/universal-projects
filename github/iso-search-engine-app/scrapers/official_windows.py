# /home/ubuntu/iso_search_engine/scrapers/official_windows.py

import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, quote_plus
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s") # Corrected quotes

# Reusing helper functions (consider moving to a utils module later)
def safe_request(url, timeout=15):
    """Makes a GET request with error handling."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15"
        }
        response = requests.get(url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return None

def find_links(soup, base_url, patterns):
    """Finds links matching given patterns (href contains)."""
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        absolute_href = href
        if not href.startswith(("http://", "https://")):
            try:
                absolute_href = urljoin(base_url, href)
            except Exception as e:
                logging.warning(f"Could not make absolute URL for {href} from base {base_url}: {e}")
                continue

        if any(pattern.lower() in absolute_href.lower() for pattern in patterns):
            # Filter out checksums, signatures, etc.
            if not re.search(r"\.(sha\d*sum|md5sum|asc|sig|txt)$", absolute_href.lower()): # Corrected regex quotes
                 links.append({"link": absolute_href, "source": "Official"})
    return links

def scrape_internet_archive(query, version, architecture):
    """Scrapes Internet Archive for Windows ISO downloads."""
    logging.info(f"Searching Internet Archive for: {query}, version: {version}, architecture: {architecture}")
    
    search_query = f"{query} {version} iso"
    search_url = f"https://archive.org/search?query={quote_plus(search_query)}"
    found_links = []
    
    response = safe_request(search_url)
    if not response:
        logging.error(f"Failed to retrieve search results from Internet Archive")
        return []
        
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Look for search results
    items = soup.select(".item-ia")
    logging.info(f"Found {len(items)} potential items on Internet Archive")
    
    for item in items:
        try:
            # Get item identifier
            identifier = item.get("data-identifier")
            if not identifier:
                continue
                
            # Get item title to check if it matches Windows version
            title_elem = item.select_one(".ttl")
            if not title_elem:
                continue
                
            title = title_elem.text.strip().lower()
            
            # Check if this result seems relevant
            if "windows" not in title:
                continue
                
            if version and version not in title:
                continue
                
            # Check architecture match
            arch_match = True
            if architecture:
                arch_lower = architecture.lower()
                if arch_lower == "x86_64":
                    arch_keywords = ["64", "x64", "amd64", "x86_64"]
                    if not any(k in title for k in arch_keywords):
                        arch_match = False
                elif arch_lower == "i386":
                    arch_keywords = ["32", "x86", "i386"]
                    if not any(k in title for k in arch_keywords):
                        arch_match = False
            
            if not arch_match:
                continue
            
            # Get details page URL
            details_url = f"https://archive.org/details/{identifier}"
            
            # Add to results
            link_info = {
                "link": details_url,
                "source": "Internet Archive",
                "title": title_elem.text.strip()
            }
            
            if architecture:
                link_info["architecture"] = architecture
            
            found_links.append(link_info)
            
        except Exception as e:
            logging.error(f"Error processing Internet Archive result: {e}")
            continue
    
    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique Internet Archive links for {query} {version}")
    return list(unique_links)

def scrape_windows(query, version=None, architecture=None):
    """Scrapes official Microsoft download pages and Internet Archive for Windows ISO links."""
    logging.info(f"Scraping Windows for query: {query}, version: {version}, architecture: {architecture}")
    query_lower = query.lower()
    iso_patterns = [".iso"]
    found_links = []
    processed_urls = set()

    urls_to_scrape = []
    target_url = None
    if "windows 10" in query_lower or (query_lower == "windows" and version == "10"):
        target_url = "https://www.microsoft.com/en-us/software-download/windows10ISO"
        urls_to_scrape.append(target_url)
        urls_to_scrape.append("https://www.microsoft.com/software-download/windows10")
    elif "windows 11" in query_lower or (query_lower == "windows" and version == "11"):
        target_url = "https://www.microsoft.com/en-us/software-download/windows11"
        urls_to_scrape.append(target_url)
    else:
        logging.warning(f"Unsupported Windows query: {query}. Only \"Windows 10\" or \"Windows 11\" supported.")
        return []

    # First try Microsoft's official site
    for url in urls_to_scrape:
        if url in processed_urls:
            continue
        response = safe_request(url)
        if response:
            processed_urls.add(url)
            soup = BeautifulSoup(response.text, "html.parser")

            page_links = find_links(soup, url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential direct ISO links on {url}")

            logging.warning(f"Scraping {url} with basic methods. May not find all links due to JavaScript dependency.")

    # Now search Internet Archive
    # Determine which Windows version to search for
    windows_version = None
    if "windows 10" in query_lower or (version == "10"):
        windows_version = "10"
    elif "windows 11" in query_lower or (version == "11"):
        windows_version = "11"
    else:
        windows_version = version  # Use provided version or None
        
    archive_links = scrape_internet_archive("Windows", windows_version, architecture)
    # Give these links lower priority than official links by appending them
    found_links.extend(archive_links)
    
    # Combine and deduplicate results
    unique_links_map = {}
    for link_info in found_links:
        unique_links_map[link_info["link"]] = link_info

    unique_links = list(unique_links_map.values())
    logging.info(f"Found {len(unique_links)} total unique Windows links")

    # If no direct links but we have a target URL, return that
    if not unique_links and target_url:
        logging.warning("No direct ISO links found from official sources. Microsoft primarily offers the Media Creation Tool.")
        found_links.append({
            "link": target_url,
            "source": "Official (Page Link - Use Media Tool or follow instructions)"
        })
        
    return found_links

# Example usage (for testing)
if __name__ == "__main__":
    win10_links = scrape_windows("Windows 10", "10", "x86_64")
    print("\n--- Windows 10 Links ---")
    for link in win10_links:
        print(f"[{link.get('source', 'Unknown')}] {link.get('title', '')} - {link['link']}")

    win11_links = scrape_windows("Windows 11", "11", "x86_64")
    print("\n--- Windows 11 Links ---")
    for link in win11_links:
        print(f"[{link.get('source', 'Unknown')}] {link.get('title', '')} - {link['link']}")

