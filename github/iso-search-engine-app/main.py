# /home/ubuntu/iso_search_engine/main.py

import logging
from flask import Flask, request, jsonify, render_template
import aggregator # Import the aggregator module

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route("/")
def index():
    """Serves the main HTML page."""
    return render_template("index.html")

@app.route("/search")
def search():
    """API endpoint to handle search queries."""
    query = request.args.get("q")
    version = request.args.get("version", "")
    architecture = request.args.get("arch")
    
    if not query:
        return jsonify({"error": "Missing query parameter 'q'."}), 400
    if not architecture:
        return jsonify({"error": "Missing architecture parameter 'arch'."}), 400

    logging.info(f"Received search request for: {query}, version: {version}, architecture: {architecture}")
    try:
        results = aggregator.search_isos(query, version, architecture)
        logging.info(f"Returning {len(results)} results for query: {query}")
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error during search aggregation for query \"{query}\": {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred during search."}), 500

if __name__ == "__main__":
    # Run the app
    # Listen on 0.0.0.0 to be accessible externally if needed
    logging.info("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000, debug=True) # Enable debug mode for detailed logs

