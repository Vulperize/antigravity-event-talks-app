import hashlib
import time
import threading
import xml.etree.ElementTree as ET
from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

FEED_URL = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"

# In-memory cache store
releases_cache = {
    "data": None,
    "last_updated": 0,
    "last_failed": 0
}
CACHE_TIMEOUT_SECONDS = 3600  # 1 hour
FAILURE_COOLDOWN_SECONDS = 300  # 5 minutes
cache_lock = threading.Lock()

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
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    now = time.time()
    
    # Check if cache needs refresh
    needs_refresh = (
        force_refresh or 
        not releases_cache["data"] or 
        (now - releases_cache["last_updated"] > CACHE_TIMEOUT_SECONDS)
    )
    
    # If it needs refresh, respect the failure cooldown unless it's a forced refresh
    if needs_refresh and not force_refresh:
        if now - releases_cache["last_failed"] < FAILURE_COOLDOWN_SECONDS:
            needs_refresh = False

    if needs_refresh:
        # If we have stale data and this is not a forced refresh, acquire lock non-blockingly.
        # This allows concurrent requests to serve stale data immediately without waiting.
        can_block = not releases_cache["data"] or force_refresh
        acquired = cache_lock.acquire(blocking=can_block)
        
        if acquired:
            try:
                # Recheck inside lock (double-checked locking)
                now = time.time()
                needs_refresh_inner = (
                    force_refresh or 
                    not releases_cache["data"] or 
                    (now - releases_cache["last_updated"] > CACHE_TIMEOUT_SECONDS)
                )
                if needs_refresh_inner and (force_refresh or now - releases_cache["last_failed"] >= FAILURE_COOLDOWN_SECONDS):
                    try:
                        response = requests.get(FEED_URL, timeout=10)
                        if response.status_code == 200:
                            releases_cache["data"] = parse_xml_feed(response.content)
                            releases_cache["last_updated"] = now
                            releases_cache["last_failed"] = 0
                        else:
                            app.logger.error("Failed to fetch feed: HTTP %d", response.status_code)
                            releases_cache["last_failed"] = now
                            if not releases_cache["data"]:
                                return jsonify({"error": "Failed to fetch remote feed"}), 500
                    except Exception as e:
                        releases_cache["last_failed"] = now
                        if not releases_cache["data"]:
                            app.logger.error("Failed to fetch/parse feed: %s", e)
                            return jsonify({"error": "An unexpected error occurred while fetching release notes"}), 500
                        else:
                            app.logger.warning("Failed to fetch/parse feed, serving stale cached data: %s", e)
            finally:
                cache_lock.release()
        else:
            # Could not acquire lock, serve stale data immediately
            pass

    if not releases_cache["data"]:
        return jsonify({"error": "Failed to fetch remote feed"}), 500
        
    return jsonify(releases_cache["data"])

if __name__ == '__main__':
    app.run(debug=True, port=5000)
