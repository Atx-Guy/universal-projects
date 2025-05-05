# /home/ubuntu/iso_search_engine/scrapers/official_linux.py

import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin # Import urljoin at the top
import re # Import re for regex matching

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s") # Corrected quotes

# --- Helper Functions ---
def safe_request(url, timeout=15): # Increased timeout slightly
    """Makes a GET request with error handling."""
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "ISO Search Bot v1.0"}) # Use a more specific User-Agent
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return None

def find_links(soup, base_url, patterns, architecture=None):
    """Finds links matching given patterns (href contains) and optionally filters by architecture."""
    links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        absolute_href = href # Assume absolute initially
        # Ensure the link is absolute
        if not href.startswith(("http://", "https://", "ftp://", "magnet:")):
            try:
                absolute_href = urljoin(base_url, href)
            except Exception as e:
                logging.warning(f"Could not make absolute URL for {href} from base {base_url}: {e}")
                continue # Skip if cannot form absolute URL

        # Check if href matches any pattern
        if any(pattern.lower() in absolute_href.lower() for pattern in patterns):
            # Basic check to filter out checksums (.sha256sum, .md5sum, etc.) and signatures (.asc, .sig)
            if not re.search(r"\.(sha\d*sum|md5sum|asc|sig|txt)$", absolute_href.lower()):
                # Add architecture info to link metadata and filter if specified
                link_info = {"link": absolute_href, "source": "Official"}
                
                # Try to detect architecture from link
                href_lower = absolute_href.lower()
                
                if "amd64" in href_lower or "x86_64" in href_lower:
                    link_info["architecture"] = "x86_64"
                elif "i386" in href_lower or "i686" in href_lower or "x86" in href_lower:
                    link_info["architecture"] = "i386"
                elif "arm64" in href_lower or "aarch64" in href_lower:
                    link_info["architecture"] = "aarch64"
                elif "armhf" in href_lower or "armv7" in href_lower:
                    link_info["architecture"] = "armhf"
                elif "ppc64" in href_lower or "powerpc64" in href_lower:
                    link_info["architecture"] = "ppc64el"
                elif "s390x" in href_lower:
                    link_info["architecture"] = "s390x"
                
                # Include the link if no architecture filter is specified
                # or if the architecture matches
                if not architecture or not link_info.get("architecture") or architecture.lower() in link_info.get("architecture", "").lower():
                    links.append(link_info)
    return links

# --- Scraper Functions ---

def scrape_ubuntu(query):
    """Scrapes official Ubuntu download pages for ISO links matching the query."""
    logging.info(f"Scraping Ubuntu for query: {query}")
    version = query.lower().replace("ubuntu", "").strip()
    iso_patterns = [".iso"]
    if version:
        version_pattern = version.replace(".", "-")
        iso_patterns.append(f"ubuntu-{version_pattern}")
        iso_patterns.append(f"ubuntu-{version}")

    urls_to_scrape = [
        "https://ubuntu.com/download/desktop",
        "https://ubuntu.com/download/server",
        "https://releases.ubuntu.com/"
    ]
    if version and ("." in version or version.isalpha()):
        urls_to_scrape.append(f"https://releases.ubuntu.com/{version}/")

    found_links = []
    processed_urls = set()
    for url in urls_to_scrape:
        if url in processed_urls:
            continue
        response = safe_request(url)
        if response:
            processed_urls.add(url)
            soup = BeautifulSoup(response.text, "html.parser")
            page_links = find_links(soup, url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential links on {url}")
            if url == "https://releases.ubuntu.com/":
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if href.endswith("/") and (href.strip("/").replace(".", "").isdigit() or href.strip("/").isalpha()):
                        release_page_url = urljoin(url, href)
                        if release_page_url not in processed_urls:
                            logging.info(f"Found potential release page: {release_page_url}")
                            release_response = safe_request(release_page_url)
                            if release_response:
                                processed_urls.add(release_page_url)
                                release_soup = BeautifulSoup(release_response.text, "html.parser")
                                release_page_links = find_links(release_soup, release_page_url, iso_patterns)
                                found_links.extend(release_page_links)
                                logging.info(f"Found {len(release_page_links)} potential links on {release_page_url}")

    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique Ubuntu links for query \"{query}\"")
    return list(unique_links)

def scrape_fedora(query):
    """Scrapes official Fedora download pages for ISO links matching the query."""
    logging.info(f"Scraping Fedora for query: {query}")
    version = query.lower().replace("fedora", "").strip()
    iso_patterns = [".iso"]
    if version:
        iso_patterns.append(f"Fedora-{version}")
        iso_patterns.append(f"Fedora-Workstation-Live-{version}")
        iso_patterns.append(f"Fedora-Server-dvd-{version}")

    urls_to_scrape = [
        "https://fedoraproject.org/workstation/download/",
        "https://fedoraproject.org/server/download/",
    ]
    found_links = []
    processed_urls = set()
    for url in urls_to_scrape:
        if url in processed_urls:
            continue
        response = safe_request(url)
        if response:
            processed_urls.add(url)
            soup = BeautifulSoup(response.text, "html.parser")
            page_links = find_links(soup, url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential links on {url}")
            mirror_patterns = ["download.fedoraproject.org/pub/fedora/linux/releases/"]
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                absolute_href = href
                if not href.startswith(("http://", "https://")):
                    try:
                        absolute_href = urljoin(url, href)
                    except Exception:
                        continue
                if any(pattern in absolute_href for pattern in mirror_patterns):
                     if ".iso" in absolute_href and not re.search(r"\.(sha\d*sum|md5sum|asc|sig|txt)$", absolute_href.lower()): # Corrected regex quotes
                         found_links.append({"link": absolute_href, "source": "Official"})
                         logging.info(f"Found potential mirror link: {absolute_href}")

    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique Fedora links for query \"{query}\"")
    return list(unique_links)

def scrape_debian(query):
    """Scrapes official Debian download pages for ISO links matching the query."""
    logging.info(f"Scraping Debian for query: {query}")
    version_part = query.lower().replace("debian", "").strip()
    iso_patterns = [".iso"]
    if version_part:
        iso_patterns.append(f"debian-{version_part}")
        iso_patterns.append(f"debian-live-{version_part}")

    urls_to_scrape = [
        "https://www.debian.org/distrib/",
        "https://www.debian.org/CD/http-ftp/",
        "https://www.debian.org/CD/live/",
        "https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/",
        "https://cdimage.debian.org/debian-cd/current/amd64/iso-dvd/",
        "https://cdimage.debian.org/debian-cd/current-live/amd64/iso-hybrid/"
    ]
    # Add older releases page if version looks like a number (e.g., 11)
    if version_part.isdigit():
        urls_to_scrape.append(f"https://cdimage.debian.org/cdimage/archive/{version_part}.0/amd64/iso-cd/")
        urls_to_scrape.append(f"https://cdimage.debian.org/cdimage/archive/{version_part}.0/amd64/iso-dvd/")

    found_links = []
    processed_urls = set()
    for url in urls_to_scrape:
        if url in processed_urls:
            continue
        response = safe_request(url)
        if response:
            processed_urls.add(url)
            soup = BeautifulSoup(response.text, "html.parser")
            page_links = find_links(soup, url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential links on {url}")
            if "cdimage.debian.org" in url:
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if href.endswith("/") and href != "../":
                        potential_dir_url = urljoin(url, href)
                        if potential_dir_url not in processed_urls:
                             if "debian-cd" in potential_dir_url or "debian-live" in potential_dir_url or "archive" in potential_dir_url:
                                logging.info(f"Found potential directory link: {potential_dir_url}")
                                dir_response = safe_request(potential_dir_url)
                                if dir_response:
                                    processed_urls.add(potential_dir_url)
                                    dir_soup = BeautifulSoup(dir_response.text, "html.parser")
                                    dir_links = find_links(dir_soup, potential_dir_url, iso_patterns)
                                    found_links.extend(dir_links)
                                    logging.info(f"Found {len(dir_links)} potential links in directory {potential_dir_url}")

    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique Debian links for query \"{query}\"")
    return list(unique_links)

def scrape_linux_mint(query):
    """Scrapes official Linux Mint download pages for ISO links."""
    logging.info(f"Scraping Linux Mint for query: {query}")
    version_part = query.lower().replace("linux mint", "").replace("mint", "").strip()
    iso_patterns = [".iso"]
    if version_part:
        iso_patterns.append(f"linuxmint-{version_part}")

    main_download_url = "https://www.linuxmint.com/download.php"
    all_versions_url = "https://linuxmint.com/download_all.php"
    lmde_url = "https://linuxmint.com/download_lmde.php"

    urls_to_scrape = [main_download_url, all_versions_url, lmde_url]
    edition_pages = set()

    found_links = []
    processed_urls = set()

    for url in urls_to_scrape:
        if url in processed_urls:
            continue
        response = safe_request(url)
        if response:
            processed_urls.add(url)
            soup = BeautifulSoup(response.text, "html.parser")
            page_links = find_links(soup, url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential direct links on {url}")

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "edition.php?id=" in href:
                    edition_url = urljoin(url, href)
                    edition_pages.add(edition_url)
                    logging.info(f"Found potential edition page: {edition_url}")

    for url in edition_pages:
        if url in processed_urls:
            continue
        response = safe_request(url)
        if response:
            processed_urls.add(url)
            soup = BeautifulSoup(response.text, "html.parser")
            page_links = find_links(soup, url, iso_patterns)
            found_links.extend(page_links)
            logging.info(f"Found {len(page_links)} potential links on edition page {url}")
            torrent_patterns = [".torrent"]
            torrent_links = find_links(soup, url, torrent_patterns)
            found_links.extend(torrent_links)
            logging.info(f"Found {len(torrent_links)} potential torrent links on edition page {url}")

    unique_links = {link["link"]: link for link in found_links}.values()
    logging.info(f"Found {len(unique_links)} unique Linux Mint links for query \"{query}\"")
    return list(unique_links)

# --- Main function for this module ---

def scrape(distro, query, version=None, architecture=None):
    """Calls the appropriate scraper based on the distribution name and filters by version and architecture."""
    distro_lower = distro.lower()
    
    # Function wrapper to add version and architecture filtering
    def scrape_with_filters(scraper_func, query):
        results = scraper_func(query)
        filtered_results = []
        
        for link_info in results:
            href_lower = link_info["link"].lower()
            
            # Detect architecture from link if not already detected
            if "architecture" not in link_info:
                if "amd64" in href_lower or "x86_64" in href_lower:
                    link_info["architecture"] = "x86_64"
                elif "i386" in href_lower or "i686" in href_lower or "x86" in href_lower:
                    link_info["architecture"] = "i386"  
                elif "arm64" in href_lower or "aarch64" in href_lower:
                    link_info["architecture"] = "aarch64"
                elif "armhf" in href_lower or "armv7" in href_lower:
                    link_info["architecture"] = "armhf"
                elif "ppc64" in href_lower or "powerpc64" in href_lower:
                    link_info["architecture"] = "ppc64el"
                elif "s390x" in href_lower:
                    link_info["architecture"] = "s390x"
            
            # Apply version filter if specified
            if version:
                version_match = False
                version_variations = [
                    version,
                    version.replace(".", "-"),
                    f"-{version}-",
                    f"/{version}/",
                    f"_{version}_",
                    f"{version}_"
                ]
                
                if any(var in href_lower for var in version_variations):
                    version_match = True
                    # Add version info to link metadata
                    link_info["version"] = version
                
                if not version_match:
                    continue  # Skip if no version match
            
            # Apply architecture filter if specified
            if architecture and link_info.get("architecture"):
                if architecture.lower() not in link_info.get("architecture", "").lower():
                    continue  # Skip if no architecture match
                    
            filtered_results.append(link_info)
                
        logging.info(f"Filtered {len(results)} links to {len(filtered_results)} matching filters: version={version}, architecture={architecture}")
        return filtered_results
    
    if distro_lower == "ubuntu":
        return scrape_with_filters(scrape_ubuntu, query)
    elif distro_lower == "fedora":
        return scrape_with_filters(scrape_fedora, query)
    elif distro_lower == "debian":
        return scrape_with_filters(scrape_debian, query)
    elif distro_lower == "linux mint" or distro_lower == "mint":
        return scrape_with_filters(scrape_linux_mint, query)
    else:
        logging.warning(f"Unsupported Linux distribution: {distro}")
        return []

# Example usage (for testing)
if __name__ == "__main__":
    # Test Ubuntu scraper
    # ubuntu_links = scrape("ubuntu", "ubuntu 24.04")
    # print("\n--- Ubuntu Links ---")
    # for link in ubuntu_links:
    #     print(link)

    # Test Fedora scraper
    # fedora_links = scrape("fedora", "fedora 42")
    # print("\n--- Fedora Links ---")
    # for link in fedora_links:
    #     print(link)

    # Test Debian scraper
    # debian_links = scrape("debian", "debian 12")
    # print("\n--- Debian Links ---")
    # for link in debian_links:
    #     print(link)

    # Test Linux Mint scraper
    mint_links = scrape("Linux Mint", "Mint 21.3")
    print("\n--- Linux Mint Links ---")
    for link in mint_links:
        print(link)

