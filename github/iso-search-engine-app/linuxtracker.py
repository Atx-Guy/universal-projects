# /home/ubuntu/iso_search_engine/scrapers/linuxtracker.py

import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin, quote_plus # quote_plus for URL encoding the query
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s") # Corrected quotes

# Reusing helper functions (consider moving to a utils module later)
def safe_request(url, timeout=20): # Increased timeout for potentially slower tracker sites
    """Makes a GET request with error handling."""
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "ISO Search Bot v1.0"})
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return None

def scrape_linuxtracker(query):
    """Scrapes Linuxtracker.org for relevant torrent links."""
    logging.info(f"Scraping Linuxtracker for query: {query}")
    base_search_url = "https://linuxtracker.org/index.php?page=torrents&options=0&active=0&category=0&search="
    search_url = base_search_url + quote_plus(query)
    query_parts = query.lower().split()

    response = safe_request(search_url)
    if not response:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    found_links = []

    torrent_tables = soup.find_all("table", class_="lista")

    if not torrent_tables:
        logging.warning("Could not find torrent table (class=\"lista\") on Linuxtracker search results page.")
        return []

    torrent_table = torrent_tables[0]

    for row in torrent_table.find_all("tr")[1:]:
        columns = row.find_all("td")
        if len(columns) >= 9:
            name_cell = columns[1]
            link_cell = columns[2]

            name_tag = name_cell.find("a")
            if name_tag:
                name_text = name_tag.get_text(strip=True).lower()
                if all(part in name_text for part in query_parts):
                    dl_link_tag = link_cell.find("a", href=True)
                    if dl_link_tag:
                        href = dl_link_tag["href"]
                        if href.endswith(".torrent") or href.startswith("magnet:"):
                            absolute_href = href
                            if not href.startswith(("http://", "https://", "magnet:")):
                                try:
                                    absolute_href = urljoin(search_url, href)
                                except Exception as e:
                                    logging.warning(f"Could not make absolute URL for {href} from base {search_url}: {e}")
                                    continue

                            found_links.append({"link": absolute_href, "source": "Linuxtracker"})
                            logging.info(f"Found Linuxtracker match: {name_text} -> {absolute_href}")

    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique Linuxtracker links for query \"{query}\"")
    return list(unique_links)

# Example usage (for testing)
if __name__ == "__main__":
    lt_links = scrape_linuxtracker("Ubuntu 24.04")
    print("\n--- Linuxtracker Links ---")
    if lt_links:
        for link in lt_links:
            print(link)
    else:
        print("No matching torrents found on Linuxtracker for the query.")

    lt_links_debian = scrape_linuxtracker("Debian 12 DVD")
    print("\n--- Linuxtracker Links (Debian) ---")
    if lt_links_debian:
        for link in lt_links_debian:
            print(link)
    else:
        print("No matching torrents found on Linuxtracker for the query.")

