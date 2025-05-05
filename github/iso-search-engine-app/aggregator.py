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

def search_isos(query, version, architecture):
    """Aggregates search results from all relevant scrapers."""
    logging.info(f"Aggregating search results for query: {query}, version: {version}, architecture: {architecture}")
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
            # Pass distro name, search query (with version), version, and architecture to official_linux.scrape
            scrapers_to_run.append((official_linux.scrape, (distro, search_query, version, architecture)))
            # Pass search query (with version), version, and architecture to other scrapers
            scrapers_to_run.append((distrowatch.scrape_distrowatch, (search_query, version, architecture)))
            scrapers_to_run.append((linuxtracker.scrape_linuxtracker, (search_query, version, architecture)))
            break # Assume only one distro per query for now

    # Windows
    if "windows" in query_lower:
        scrapers_to_run.append((official_windows.scrape_windows, (search_query, version, architecture)))
        # Optionally add torrent sites for Windows if desired
        # scrapers_to_run.append((linuxtracker.scrape_linuxtracker, (search_query, version, architecture)))

    if not scrapers_to_run:
        logging.warning(f"No relevant scrapers identified for query: {query}")
        return []

    # Run scrapers concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit scraper tasks
        future_to_scraper = {executor.submit(run_scraper, func, args): func.__name__ for func, args in scrapers_to_run}

        for future in concurrent.futures.as_completed(future_to_scraper):
            scraper_name = future_to_scraper[future]
            try:
                results = future.result()
                if results:
                    all_links.extend(results)
                    logging.info(f"Scraper {scraper_name} returned {len(results)} results.")
                else:
                    logging.info(f"Scraper {scraper_name} returned no results.")
            except Exception as exc:
                logging.error(f"Scraper {scraper_name} generated an exception: {exc}", exc_info=True)

    # Deduplicate results based on the link URL
    unique_links_map = {}
    for link_info in all_links:
        link_url = link_info.get("link")
        if link_url:
            # Skip links that don't match the version filter (if specified)
            if version and not link_matches_version(link_url, version):
                continue
                
            # Filter by architecture if it's included in the link info
            link_arch = link_info.get("architecture", "").lower()
            if link_arch and architecture.lower() not in link_arch:
                continue
                
            # If link already exists, keep the one with higher priority (lower number)
            existing_priority = SOURCE_PRIORITY.get(unique_links_map.get(link_url, {}).get("source"), DEFAULT_PRIORITY)
            current_priority = SOURCE_PRIORITY.get(link_info.get("source"), DEFAULT_PRIORITY)
            if current_priority < existing_priority:
                unique_links_map[link_url] = link_info

    # Sort results based on priority, then alphabetically by link
    sorted_links = sorted(
        unique_links_map.values(),
        key=lambda x: (SOURCE_PRIORITY.get(x.get("source"), DEFAULT_PRIORITY), x.get("link"))
    )

    logging.info(f"Aggregated {len(sorted_links)} unique links for query \"{query}\" with version \"{version}\" and architecture \"{architecture}\"")
    return sorted_links

def link_matches_version(link, version):
    """Checks if a link matches the specified version."""
    if not version:
        return True
        
    link_lower = link.lower()
    version_variations = [
        version,
        version.replace(".", "-"),
        f"-{version}-",
        f"/{version}/",
        f"_{version}_",
        f"{version}_"
    ]
    
    return any(var in link_lower for var in version_variations)

# Example usage (for testing)
if __name__ == "__main__":
    test_query_ubuntu = "Ubuntu"
    test_version_ubuntu = "24.04"
    test_architecture_ubuntu = "x86_64"
    print(f"\n--- Aggregated Results for: {test_query_ubuntu}, Version: {test_version_ubuntu}, Architecture: {test_architecture_ubuntu} ---")
    results_ubuntu = search_isos(test_query_ubuntu, test_version_ubuntu, test_architecture_ubuntu)
    for link in results_ubuntu:
        print(f"[{link['source']}] {link['link']}") # Use standard quotes

    test_query_windows = "Windows"
    test_version_windows = "11"
    test_architecture_windows = "x86_64"
    print(f"\n--- Aggregated Results for: {test_query_windows}, Version: {test_version_windows}, Architecture: {test_architecture_windows} ---")
    results_windows = search_isos(test_query_windows, test_version_windows, test_architecture_windows)
    for link in results_windows:
        print(f"[{link['source']}] {link['link']}") # Use standard quotes

    test_query_debian = "Debian"
    test_version_debian = "12"
    test_architecture_debian = "arm64"
    print(f"\n--- Aggregated Results for: {test_query_debian}, Version: {test_version_debian}, Architecture: {test_architecture_debian} ---")
    results_debian = search_isos(test_query_debian, test_version_debian, test_architecture_debian)
    for link in results_debian:
        print(f"[{link['source']}] {link['link']}") # Use standard quotes

