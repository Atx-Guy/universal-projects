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
    
    # Create a more specific search query based on version
    if version == "vista":
        search_query = "Windows Vista ISO"
    else:
        search_query = f"Windows {version} ISO"
        
    # Add architecture to search query if specified
    if architecture:
        if architecture == "x86_64":
            search_query += " 64-bit OR 64bit OR x64 OR amd64"
        elif architecture == "i386":
            search_query += " 32-bit OR 32bit OR x86"
    
    logging.info(f"Searching Internet Archive with query: {search_query}")
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
                
            # Get item title
            title_elem = item.select_one(".ttl")
            if not title_elem:
                continue
                
            title = title_elem.text.strip()
            title_lower = title.lower()
            
            # Check if this result seems relevant to Windows
            if "windows" not in title_lower:
                continue
            
            # Version matching based on the selected version
            version_match = False
            if version == "11" and ("windows 11" in title_lower or "windows11" in title_lower):
                version_match = True
            elif version == "10" and ("windows 10" in title_lower or "windows10" in title_lower):
                version_match = True
            elif version == "8.1" and ("windows 8.1" in title_lower or "windows8.1" in title_lower):
                version_match = True
            elif version == "8" and ("windows 8" in title_lower and "8.1" not in title_lower):
                version_match = True
            elif version == "7" and ("windows 7" in title_lower or "windows7" in title_lower):
                version_match = True
            elif version == "vista" and ("windows vista" in title_lower or "windowsvista" in title_lower):
                version_match = True
                
            if not version_match:
                continue
                
            # Check architecture match if specified
            arch_match = True
            if architecture:
                arch_lower = architecture.lower()
                if arch_lower == "x86_64":
                    arch_keywords = ["64", "x64", "amd64", "x86_64"]
                    if not any(k in title_lower for k in arch_keywords):
                        arch_match = False
                elif arch_lower == "i386":
                    arch_keywords = ["32", "x86", "i386"]
                    if not any(k in title_lower for k in arch_keywords) and all(k not in title_lower for k in ["64", "x64", "amd64"]):
                        # If no explicit 32-bit mention, and also no 64-bit mention, assume it might be 32-bit
                        pass
                    elif not any(k in title_lower for k in arch_keywords):
                        arch_match = False
            
            if not arch_match:
                continue
            
            # Get details page URL
            details_url = f"https://archive.org/details/{identifier}"
            
            # Add to results
            link_info = {
                "link": details_url,
                "source": "Internet Archive",
                "title": title
            }
            
            # Set architecture information
            if "64" in title_lower or "x64" in title_lower or "amd64" in title_lower:
                link_info["architecture"] = "x86_64"
            elif "32" in title_lower or "x86" in title_lower or "i386" in title_lower:
                link_info["architecture"] = "i386"
            elif architecture:
                link_info["architecture"] = architecture
            
            found_links.append(link_info)
            logging.info(f"Found matching Windows ISO: {title}")
            
        except Exception as e:
            logging.error(f"Error processing Internet Archive result: {e}")
            continue
    
    logging.info(f"Found {len(found_links)} Windows ISOs on Internet Archive for version {version}")
    return found_links

def scrape_windows(query, version=None, architecture=None):
    """Scrapes official Microsoft download pages and Internet Archive for Windows ISO links."""
    logging.info(f"Scraping Windows for query: {query}, version: {version}, architecture: {architecture}")
    query_lower = query.lower()
    iso_patterns = [".iso"]
    found_links = []

    # Microsoft official download links only exist for Windows 10 and 11
    # For older versions, we'll go straight to Internet Archive
    target_url = None
    if version == "11" or "windows 11" in query_lower:
        target_url = "https://www.microsoft.com/en-us/software-download/windows11"
        
        # Try Microsoft's official site for Windows 11
        response = safe_request(target_url)
        if response:
            soup = BeautifulSoup(response.text, "html.parser")
            page_links = find_links(soup, target_url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential direct ISO links on {target_url}")
            
            # Even if no direct links found, keep the official tool URL
            if not page_links:
                found_links.append({
                    "link": target_url,
                    "source": "Official (Page Link - Use Media Tool or follow instructions)"
                })
                
    elif version == "10" or "windows 10" in query_lower:
        target_url = "https://www.microsoft.com/en-us/software-download/windows10ISO"
        
        # Try Microsoft's official site for Windows 10
        response = safe_request(target_url)
        if response:
            soup = BeautifulSoup(response.text, "html.parser")
            page_links = find_links(soup, target_url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential direct ISO links on {target_url}")
            
            # Even if no direct links found, keep the official tool URL
            if not page_links:
                found_links.append({
                    "link": target_url,
                    "source": "Official (Page Link - Use Media Tool or follow instructions)"
                })
    
    # For all Windows versions (including 10 and 11), search Internet Archive
    # This will be the only source for Windows 7, 8, 8.1, and Vista
    archive_links = scrape_internet_archive("Windows", version, architecture)
    found_links.extend(archive_links)
    
    # Combine and deduplicate results
    unique_links_map = {}
    for link_info in found_links:
        unique_links_map[link_info["link"]] = link_info

    unique_links = list(unique_links_map.values())
    logging.info(f"Found {len(unique_links)} total unique Windows links for version {version}")
    
    return unique_links

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

