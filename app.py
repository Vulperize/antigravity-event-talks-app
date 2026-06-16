import hashlib
import logging
import xml.etree.ElementTree as ET
from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

FEED_URL = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"

# Configure logging
logging.basicConfig(level=logging.INFO)

def parse_xml_feed(xml_content):
    root = ET.fromstring(xml_content)
    # The RSS feed uses Atom namespace
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    items = []
    
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns)
        title_text = (title.text if title is not None else None) or "No Title"
        
        updated = entry.find('atom:updated', ns)
        updated_text = (updated.text if updated is not None else None) or ""
        # Format date (e.g., "2026-06-16T09:00:00Z" -> "2026-06-16")
        date_short = updated_text[:10] if updated_text else ""
        
        content = entry.find('atom:content', ns)
        content_html = (content.text if content is not None else None) or ""
        
        # ID generation based on title and date
        item_id = hashlib.sha256((title_text + date_short).encode('utf-8')).hexdigest()[:16]
        
        # Simple category deduction based on keywords
        note_type = "CHANGE"
        content_upper = content_html.upper()
        if "FEATURE" in content_upper or "NEW:" in content_upper or "INTRODUCED" in content_upper:
            note_type = "FEATURE"
        elif "DEPRECATE" in content_upper or "DISCONTINUE" in content_upper or "REMOVED" in content_upper:
            note_type = "DEPRECATION"
        elif "BUG" in content_upper or "FIX" in content_upper or "RESOLVED" in content_upper:
            note_type = "BUGFIX"
            
        items.append({
            "id": item_id,
            "title": title_text,
            "date": date_short,
            "type": note_type,
            "content": content_html
        })
    return items

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/releases')
def get_releases():
    try:
        response = requests.get(FEED_URL, timeout=10)
        if response.status_code == 200:
            data = parse_xml_feed(response.content)
            return jsonify(data)
        logging.error("Failed to fetch feed: HTTP %d", response.status_code)
        return jsonify({"error": "An unexpected error occurred while fetching release notes"}), 500
    except Exception as e:
        logging.error("Failed to fetch/parse feed: %s", e)
        return jsonify({"error": "An unexpected error occurred while fetching release notes"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
