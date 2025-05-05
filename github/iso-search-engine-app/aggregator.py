# /home/ubuntu/iso_search_engine/aggregator.py

import logging
import concurrent.futures

# Import scraper functions from the scrapers package
from scrapers import official_linux, official_windows, distrowatch, linuxtracker

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define source priorities
SOURCE_PRIORITY = {
    "Official": 1,
    "Official (Page Link - Use Media Tool or follow instructions)": 2, # Lower priority official link
    "DistroWatch": 3,
    "Linuxtracker": 4,
    "Internet Archive": 5, # Adding Internet Archive as a source
}
DEFAULT_PRIORITY = 99

def run_scraper(scraper_func, query_tuple):
    """Runs a scraper function with error handling."""
    try:
        # Unpack the query tuple which might contain one or two arguments
        return scraper_func(*query_tuple)
    except Exception as e:
        logging.error(f"Error running scraper {scraper_func.__name__} for query \"{query_tuple}\": {e}", exc_info=True)
        return []

def search_isos(query, version):
    """Aggregates search results from all relevant scrapers."""
    logging.info(f"Aggregating search results for query: {query}, version: {version}")
    query_lower = query.lower()
    all_links = []

    # If specific version is selected, append it to query if not already present
    search_query = query
    if version and version not in query_lower:
        search_query = f"{query} {version}"
        logging.info(f"Appended version to query: {search_query}")

    # Determine which scrapers to run based on the query
    scrapers_to_run = []

    # Linux Distros
    linux_distros = ["ubuntu", "fedora", "debian", "linux mint", "mint"]
    matched_distro = None
    for distro in linux_distros:
        if distro in query_lower:
            matched_distro = distro
            # Pass distro name, search query (with version), and version to official_linux.scrape
            scrapers_to_run.append((official_linux.scrape, (distro, search_query, version)))
            # Pass search query (with version) and version to other scrapers
            scrapers_to_run.append((distrowatch.scrape_distrowatch, (search_query, version)))
            scrapers_to_run.append((linuxtracker.scrape_linuxtracker, (search_query, version)))
            break # Assume only one distro per query for now

    # Windows
    if "windows" in query_lower:
        # Try to infer architecture from query
        architecture = None
        if "64" in query_lower or "x64" in query_lower or "amd64" in query_lower:
            architecture = "x86_64"
        elif "32" in query_lower or "x86" in query_lower or "i386" in query_lower:
            architecture = "i386"
            
        # Pass query, version, and architecture to the Windows scraper
        scrapers_to_run.append((official_windows.scrape_windows, (search_query, version, architecture)))
        
        # For older Windows versions (Vista, 7, 8), try both architectures if not specified
        if version in ["vista", "7", "8", "8.1"] and architecture is None:
            scrapers_to_run.append((official_windows.scrape_windows, (search_query, version, "x86_64")))
            scrapers_to_run.append((official_windows.scrape_windows, (search_query, version, "i386")))
            
        # Optionally add torrent sites for Windows if desired
        # scrapers_to_run.append((linuxtracker.scrape_linuxtracker, (search_query, version)))

