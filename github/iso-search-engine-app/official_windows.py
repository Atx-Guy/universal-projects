# /home/ubuntu/iso_search_engine/scrapers/official_windows.py

import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin
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

def scrape_windows(query):
    """Scrapes official Microsoft download pages for Windows ISO links."""
    logging.info(f"Scraping Windows for query: {query}")
    query_lower = query.lower()
    iso_patterns = [".iso"]
    found_links = []
    processed_urls = set()

    urls_to_scrape = []
    target_url = None
    if "windows 10" in query_lower:
        target_url = "https://www.microsoft.com/en-us/software-download/windows10ISO"
        urls_to_scrape.append(target_url)
        urls_to_scrape.append("https://www.microsoft.com/software-download/windows10")
    elif "windows 11" in query_lower:
        target_url = "https://www.microsoft.com/en-us/software-download/windows11"
        urls_to_scrape.append(target_url)
    else:
        logging.warning(f"Unsupported Windows query: {query}. Only \"Windows 10\" or \"Windows 11\" supported.")
        return []

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

    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique Windows links for query \"{query}\". (Note: May be incomplete)")

    if not unique_links and target_url:
        logging.warning("No direct ISO links found. Microsoft primarily offers the Media Creation Tool or requires specific interactions.")
        return [{
            "link": target_url,
            "source": "Official (Page Link - Use Media Tool or follow instructions)"
        }]

    return list(unique_links)

# Example usage (for testing)
if __name__ == "__main__":
    win10_links = scrape_windows("Windows 10")
    print("\n--- Windows 10 Links ---")
    for link in win10_links:
        print(link)

    win11_links = scrape_windows("Windows 11")
    print("\n--- Windows 11 Links ---")
    for link in win11_links:
        print(link)

