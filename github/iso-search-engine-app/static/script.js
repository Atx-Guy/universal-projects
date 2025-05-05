// /home/ubuntu/iso_search_engine/static/script.js

document.addEventListener("DOMContentLoaded", () => {
    const searchForm = document.getElementById("search-form");
    const distroFilter = document.getElementById("distro-filter");
    const versionFilter = document.getElementById("version-filter");
    const architectureFilter = document.getElementById("architecture-filter");
    const resultsList = document.getElementById("results-list");
    const loadingIndicator = document.getElementById("loading-indicator");

    // Define available versions for each distribution
    const versionsByDistro = {
        "ubuntu": [
            { value: "24.04", label: "Ubuntu 24.04 LTS" },
            { value: "23.10", label: "Ubuntu 23.10" },
            { value: "22.04", label: "Ubuntu 22.04 LTS" },
            { value: "20.04", label: "Ubuntu 20.04 LTS" },
            { value: "18.04", label: "Ubuntu 18.04 LTS" }
        ],
        "fedora": [
            { value: "40", label: "Fedora 40" },
            { value: "39", label: "Fedora 39" },
            { value: "38", label: "Fedora 38" },
            { value: "37", label: "Fedora 37" }
        ],
        "debian": [
            { value: "12", label: "Debian 12 (Bookworm)" },
            { value: "11", label: "Debian 11 (Bullseye)" },
            { value: "10", label: "Debian 10 (Buster)" }
        ],
        "linux mint": [
            { value: "21.3", label: "Linux Mint 21.3" },
            { value: "21.2", label: "Linux Mint 21.2" },
            { value: "21.1", label: "Linux Mint 21.1" },
            { value: "20.3", label: "Linux Mint 20.3" }
        ],
        "windows": [
            { value: "11", label: "Windows 11" },
            { value: "10", label: "Windows 10" }
        ]
    };

    // Populate versions dropdown based on selected distribution
    distroFilter.addEventListener("change", () => {
        const selectedDistro = distroFilter.value;
        
        // Clear current options
        versionFilter.innerHTML = '<option value="" disabled selected>Select Version</option>';
        
        // Enable version dropdown and populate options if distribution is selected
        if (selectedDistro) {
            versionFilter.disabled = false;
            const versions = versionsByDistro[selectedDistro] || [];
            
            versions.forEach(version => {
                const option = document.createElement("option");
                option.value = version.value;
                option.textContent = version.label;
                versionFilter.appendChild(option);
            });
        } else {
            versionFilter.disabled = true;
        }
    });

    searchForm.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent default form submission
        const distro = distroFilter.value;
        const version = versionFilter.value;
        const architecture = architectureFilter.value;

        if (!distro || !version || !architecture) {
            return; // Don't search if any required field is empty
        }

        // Clear previous results and show loading indicator
        resultsList.innerHTML = "";
        loadingIndicator.style.display = "block";

        try {
            // Create search query from selected options
            const query = distro;
            
            // Make API call to the backend with all parameters
            const response = await fetch(`/search?q=${encodeURIComponent(query)}&version=${encodeURIComponent(version)}&arch=${encodeURIComponent(architecture)}`);
            
            if (!response.ok) {
                // Handle HTTP errors
                let errorMsg = `Error: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (e) { /* Ignore if response is not JSON */ }
                throw new Error(errorMsg);
            }

            const results = await response.json();

            // Hide loading indicator
            loadingIndicator.style.display = "none";

            // Display results
            if (results && results.length > 0) {
                results.forEach(item => {
                    const listItem = document.createElement("li");
                    
                    // Create source span
                    const sourceSpan = document.createElement("span");
                    sourceSpan.textContent = item.source;
                    // Create a CSS-friendly class name from the source string
                    const sourceClass = item.source.replace(/[^a-zA-Z0-9]/g, "-"); 
                    sourceSpan.className = `source source-${sourceClass}`;
                    
                    // Create link
                    const link = document.createElement("a");
                    link.href = item.link;
                    link.textContent = item.link;
                    link.target = "_blank"; // Open in new tab
                    link.rel = "noopener noreferrer";

                    listItem.appendChild(sourceSpan);
                    listItem.appendChild(link);
                    resultsList.appendChild(listItem);
                });
            } else {
                // Display no results message
                const noResultsItem = document.createElement("li");
                noResultsItem.textContent = "No results found for your query.";
                resultsList.appendChild(noResultsItem);
            }

        } catch (error) {
            // Hide loading indicator and display error
            loadingIndicator.style.display = "none";
            const errorItem = document.createElement("li");
            errorItem.textContent = `Search failed: ${error.message}`;
            errorItem.style.color = "red";
            resultsList.appendChild(errorItem);
            console.error("Search failed:", error);
        }
    });
});

