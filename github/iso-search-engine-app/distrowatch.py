# /home/ubuntu/iso_search_engine/scrapers/distrowatch.py

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
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "ISO Search Bot v1.0"})
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return None

def scrape_distrowatch(query):
    """Scrapes the DistroWatch torrent archive page for relevant torrent links."""
    logging.info(f"Scraping DistroWatch for query: {query}")
    distrowatch_url = "https://distrowatch.com/dwres.php?resource=bittorrent"
    query_parts = query.lower().split()

    response = safe_request(distrowatch_url)
    if not response:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    found_links = []

    news_cells = soup.find_all("td", class_="News1")

    for cell in news_cells:
        tables = cell.find_all("table")
        for table in tables:
            for row in table.find_all("tr"):
                columns = row.find_all("td")
                if len(columns) >= 2:
                    description_cell = columns[0]
                    link_cell = columns[-1]

                    description_text = description_cell.get_text(strip=True).lower()
                    link_tag = link_cell.find("a", href=True)

                    if all(part in description_text for part in query_parts):
                        if link_tag:
                            href = link_tag["href"]
                            if href.endswith(".torrent") or href.startswith("magnet:"):
                                absolute_href = href
                                if not href.startswith(("http://", "https://", "magnet:")):
                                    try:
                                        absolute_href = urljoin(distrowatch_url, href)
                                    except Exception as e:
                                        logging.warning(f"Could not make absolute URL for {href} from base {distrowatch_url}: {e}")
                                        continue

                                found_links.append({"link": absolute_href, "source": "DistroWatch"})
                                logging.info(f"Found DistroWatch match: {description_text} -> {absolute_href}")

    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique DistroWatch links for query \"{query}\"")
    return list(unique_links)

# Example usage (for testing)
if __name__ == "__main__":
    dw_links = scrape_distrowatch("Ubuntu 24.04")
    print("\n--- DistroWatch Links ---")
    if dw_links:
        for link in dw_links:
            print(link)
    else:
        print("No matching torrents found on DistroWatch archive page for the query.")

    dw_links_fedora = scrape_distrowatch("Fedora 42")
    print("\n--- DistroWatch Links (Fedora) ---")
    if dw_links_fedora:
        for link in dw_links_fedora:
            print(link)
    else:
        print("No matching torrents found on DistroWatch archive page for the query.")

