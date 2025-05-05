// /home/ubuntu/iso_search_engine/static/script.js

document.addEventListener("DOMContentLoaded", () => {
    const searchForm = document.getElementById("search-form");
    const searchQueryInput = document.getElementById("search-query");
    const architectureFilter = document.getElementById("architecture-filter");
    const resultsList = document.getElementById("results-list");
    const loadingIndicator = document.getElementById("loading-indicator");

    searchForm.addEventListener("submit", async (event) => {
        event.preventDefault(); // Prevent default form submission
        const query = searchQueryInput.value.trim();
        const architecture = architectureFilter.value;

        if (!query) {
            return; // Don't search if query is empty
        }

        // Clear previous results and show loading indicator
        resultsList.innerHTML = "";
        loadingIndicator.style.display = "block";

        try {
            // Make API call to the backend with both query and architecture filter
            const response = await fetch(`/search?q=${encodeURIComponent(query)}&arch=${encodeURIComponent(architecture)}`);
            
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

