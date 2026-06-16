# BigQuery Release Notes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python Flask web application that fetches Google BigQuery release notes XML, parses and displays them in a premium master-detail dashboard, supports keyword search, and shares specific notes via Twitter/X Web Intents.

**Architecture:** The Flask server retrieves the external XML feed, parses it into structured JSON objects, and caches it in-memory. The frontend uses vanilla HTML/CSS/JS to render the UI, manage local state, search/filter notes, and handle Twitter Web Intent links without full page reloads.

**Tech Stack:** Python 3, Flask, requests, HTML5, CSS3, ES6+ Javascript.

---

### Task 1: Environment Setup & Flask Shell

**Files:**
- Create: `requirements.txt`
- Create: `app.py`
- Create: `templates/index.html`

**Step 1: Write requirements.txt**
Create `requirements.txt` with Flask and requests:
```text
flask>=3.0.0
requests>=2.31.0
```

**Step 2: Create basic Flask app**
Write `app.py` serving a basic HTML index page:
```python
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

**Step 3: Create index.html shell**
Create `templates/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BigQuery Release Notes</title>
</head>
<body>
    <h1>BigQuery Release Notes Dashboard</h1>
</body>
</html>
```

**Step 4: Verify the app runs**
Run: `pip install -r requirements.txt` and then `python app.py`. Check `http://127.0.0.1:5000` is reachable.

**Step 5: Commit**
```bash
git add requirements.txt app.py templates/index.html
git commit -m "feat: init Flask environment and app shell"
```

---

### Task 2: XML Feed Fetcher and Parser

**Files:**
- Modify: `app.py`
- Create: `test_parser.py`

**Step 1: Implement parsing logic**
Add feed parsing logic to `app.py` using standard library XML parsing (`xml.etree.ElementTree`):
```python
import xml.etree.ElementTree as ET
import requests
from flask import jsonify

FEED_URL = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"

def parse_xml_feed(xml_content):
    root = ET.fromstring(xml_content)
    # The RSS feed uses Atom namespace
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    items = []
    
    for entry in root.findall('atom:entry', ns):
        title = entry.find('atom:title', ns)
        title_text = title.text if title is not None else "No Title"
        
        updated = entry.find('atom:updated', ns)
        updated_text = updated.text if updated is not None else ""
        # Format date (e.g., "2026-06-16T09:00:00Z" -> "2026-06-16")
        date_short = updated_text[:10] if updated_text else ""
        
        content = entry.find('atom:content', ns)
        content_html = content.text if content is not None else ""
        
        # ID generation based on title and date
        item_id = str(hash(title_text + date_short))
        
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

@app.route('/api/releases')
def get_releases():
    try:
        response = requests.get(FEED_URL, timeout=10)
        if response.status_code == 200:
            data = parse_xml_feed(response.content)
            return jsonify(data)
        return jsonify({"error": "Failed to fetch feed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

**Step 2: Write unit tests for the parser**
Create `test_parser.py`:
```python
import unittest
from app import parse_xml_feed

class TestParser(unittest.TestCase):
    def test_parse_valid_feed(self):
        sample_xml = """<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>BigQuery release notes: June 15, 2026</title>
                <updated>2026-06-15T12:00:00Z</updated>
                <content type="html">Feature: A new optimized storage format is now default.</content>
            </entry>
        </feed>"""
        results = parse_xml_feed(sample_xml.encode('utf-8'))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "BigQuery release notes: June 15, 2026")
        self.assertEqual(results[0]['date'], "2026-06-15")
        self.assertEqual(results[0]['type'], "FEATURE")

if __name__ == '__main__':
    unittest.main()
```

**Step 3: Run the parser tests**
Run: `python test_parser.py`
Expected output: `OK`

**Step 4: Verify the API endpoint**
Run `python app.py`, and fetch `http://127.0.0.1:5000/api/releases` in browser or curl to verify it returns parsed release note entries in JSON format.

**Step 5: Commit**
```bash
git add test_parser.py
git commit -am "feat: add XML feed parsing logic and API endpoint with unit tests"
```

---

### Task 3: In-Memory Caching

**Files:**
- Modify: `app.py`

**Step 1: Write caching logic in app.py**
Add an in-memory cache layer:
```python
import time
from flask import request

# In-memory cache store
releases_cache = {
    "data": None,
    "last_updated": 0
}
CACHE_TIMEOUT_SECONDS = 3600  # 1 hour

@app.route('/api/releases')
def get_releases():
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    now = time.time()
    
    if force_refresh or not releases_cache["data"] or (now - releases_cache["last_updated"] > CACHE_TIMEOUT_SECONDS):
        try:
            response = requests.get(FEED_URL, timeout=10)
            if response.status_code == 200:
                parsed_data = parse_xml_feed(response.content)
                releases_cache["data"] = parsed_data
                releases_cache["last_updated"] = now
            else:
                if not releases_cache["data"]:
                    return jsonify({"error": "Failed to fetch remote feed"}), 500
        except Exception as e:
            if not releases_cache["data"]:
                return jsonify({"error": str(e)}), 500
                
    return jsonify(releases_cache["data"])
```

**Step 2: Verify caching works**
1. Stop and start `python app.py`.
2. Access `http://127.0.0.1:5000/api/releases` (first load takes a second to hit Google).
3. Access it again (instant load from cache).
4. Run with `?refresh=true` to force a cache bust.

**Step 3: Commit**
```bash
git commit -am "feat: implement in-memory cache with refresh bypass"
```

---

### Task 4: UI Page Structure & Dark Theme Styling

**Files:**
- Modify: `templates/index.html`
- Create: `static/styles.css`

**Step 1: Design HTML Layout**
Update `templates/index.html` to declare the CSS links, App header, search box, filter buttons, list view, and detail panel:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BigQuery Release Notes Dashboard</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <div class="app-container">
        <!-- Header -->
        <header class="app-header">
            <div class="logo-area">
                <div class="logo-box">BQ</div>
                <h1>BigQuery Release Notes</h1>
            </div>
            <button id="refresh-btn" class="btn-primary">
                <svg id="refresh-icon" viewBox="0 0 24 24"><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
                <span>Refresh</span>
            </button>
        </header>

        <!-- Controls -->
        <section class="controls-section">
            <div class="search-wrapper">
                <span class="search-icon">🔍</span>
                <input type="text" id="search-input" placeholder="Search release notes...">
            </div>
            <div class="filter-wrapper" id="filters-container">
                <button class="filter-badge active" data-filter="ALL">All</button>
                <button class="filter-badge" data-filter="FEATURE">Features</button>
                <button class="filter-badge" data-filter="CHANGE">Changes</button>
                <button class="filter-badge" data-filter="DEPRECATION">Deprecations</button>
                <button class="filter-badge" data-filter="BUGFIX">Bugfixes</button>
            </div>
        </section>

        <!-- Dashboard Workspace -->
        <div class="workspace">
            <!-- Left Side Feed List -->
            <aside class="feed-sidebar">
                <div id="feed-list" class="feed-list">
                    <!-- Cards will be dynamically inserted here -->
                    <div class="loading-state">Loading release notes...</div>
                </div>
            </aside>

            <!-- Right Side Selected Note Details -->
            <main class="detail-pane" id="detail-pane">
                <div class="empty-state">
                    <h3>Select a release note</h3>
                    <p>Choose an item from the left pane to view details and tweet it.</p>
                </div>
            </main>
        </div>
    </div>
    <script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
```

**Step 2: Add CSS layout styling**
Create `static/styles.css` with dark theme styling, master-detail layout columns, fonts, custom scrollbars, animations, and hover state scaling. Use Outifit Google font.
```css
:root {
    --bg-dark: #0f172a;
    --bg-card: rgba(30, 41, 59, 0.7);
    --bg-card-hover: rgba(30, 41, 59, 0.9);
    --border-color: rgba(255, 255, 255, 0.08);
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --accent-blue: #38bdf8;
    --accent-hover: #0ea5e9;
    --feature-color: #38bdf8;
    --change-color: #10b981;
    --deprecation-color: #f59e0b;
    --bugfix-color: #ef4444;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    background-color: var(--bg-dark);
    color: var(--text-primary);
    font-family: 'Outfit', sans-serif;
    height: 100vh;
    overflow: hidden;
}

.app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

/* Header */
.app-header {
    background: rgba(15, 23, 42, 0.9);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border-color);
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo-area {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.logo-box {
    background: linear-gradient(135deg, #0284c7, #38bdf8);
    color: white;
    font-weight: 700;
    font-size: 1.1rem;
    width: 2.25rem;
    height: 2.25rem;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.logo-area h1 {
    font-size: 1.25rem;
    font-weight: 600;
    letter-spacing: -0.02em;
}

.btn-primary {
    background: linear-gradient(135deg, #0284c7, #0ea5e9);
    border: none;
    color: white;
    font-weight: 500;
    font-family: inherit;
    padding: 0.5rem 1.25rem;
    border-radius: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s ease;
}

.btn-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(56, 189, 248, 0.2);
}

.btn-primary svg {
    width: 1.1rem;
    height: 1.1rem;
    fill: currentColor;
}

/* Controls */
.controls-section {
    background: rgba(15, 23, 42, 0.7);
    border-bottom: 1px solid var(--border-color);
    padding: 1rem 2rem;
    display: flex;
    gap: 1.5rem;
    align-items: center;
    flex-wrap: wrap;
}

.search-wrapper {
    position: relative;
    flex: 1;
    min-width: 280px;
}

.search-icon {
    position: absolute;
    left: 0.85rem;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-secondary);
}

#search-input {
    width: 100%;
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 0.6rem 1rem 0.6rem 2.25rem;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.95rem;
    outline: none;
    transition: all 0.2s ease;
}

#search-input:focus {
    border-color: var(--accent-blue);
    background: rgba(30, 41, 59, 0.8);
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
}

.filter-wrapper {
    display: flex;
    gap: 0.5rem;
}

.filter-badge {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 0.4rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.2s ease;
}

.filter-badge:hover {
    color: var(--text-primary);
    border-color: var(--text-secondary);
}

.filter-badge.active {
    background: var(--accent-blue);
    color: var(--bg-dark);
    border-color: var(--accent-blue);
    font-weight: 600;
}

/* Workspace */
.workspace {
    display: flex;
    flex: 1;
    overflow: hidden;
}

.feed-sidebar {
    width: 380px;
    border-right: 1px solid var(--border-color);
    overflow-y: auto;
    background: rgba(15, 23, 42, 0.5);
}

.feed-list {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.detail-pane {
    flex: 1;
    overflow-y: auto;
    padding: 2rem;
    background: rgba(30, 41, 59, 0.15);
}

/* Cards */
.release-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1rem;
    cursor: pointer;
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.release-card:hover {
    transform: translateY(-2px);
    background: var(--bg-card-hover);
    border-color: rgba(56, 189, 248, 0.3);
}

.release-card.active {
    border-left: 4px solid var(--accent-blue);
    background: rgba(56, 189, 248, 0.08);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.badge {
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
}

.badge.FEATURE { background: rgba(56, 189, 248, 0.15); color: var(--feature-color); }
.badge.CHANGE { background: rgba(16, 185, 129, 0.15); color: var(--change-color); }
.badge.DEPRECATION { background: rgba(245, 158, 11, 0.15); color: var(--deprecation-color); }
.badge.BUGFIX { background: rgba(239, 68, 68, 0.15); color: var(--bugfix-color); }

.card-date {
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.release-card h3 {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.4;
}

.card-snippet {
    font-size: 0.85rem;
    color: var(--text-secondary);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* Detail View Layout */
.detail-header {
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 1.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.5rem;
}

.detail-meta {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
}

.detail-title {
    font-size: 1.5rem;
    font-weight: 700;
    line-height: 1.3;
}

.tweet-btn {
    background: #1da1f2;
    color: white;
    border: none;
    border-radius: 20px;
    padding: 0.6rem 1.25rem;
    font-weight: 600;
    font-family: inherit;
    font-size: 0.9rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    transition: all 0.2s ease;
    flex-shrink: 0;
}

.tweet-btn:hover {
    background: #1a91da;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(29, 161, 242, 0.3);
}

.tweet-btn svg {
    width: 0.95rem;
    height: 0.95rem;
    fill: currentColor;
}

.detail-content {
    font-size: 1rem;
    line-height: 1.7;
    color: #e2e8f0;
}

.detail-content p {
    margin-bottom: 1.25rem;
}

.detail-content ul, .detail-content ol {
    margin-left: 1.5rem;
    margin-bottom: 1.25rem;
}

.detail-content li {
    margin-bottom: 0.5rem;
}

.detail-content code {
    background: rgba(30, 41, 59, 0.8);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.9rem;
}

/* States */
.empty-state, .loading-state {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    color: var(--text-secondary);
    text-align: center;
    padding: 2rem;
}

.empty-state h3 {
    margin-bottom: 0.5rem;
    color: var(--text-primary);
}

/* Spin animation */
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.spinning {
    animation: spin 1s linear infinite;
}

/* Custom scrollbars */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(15, 23, 42, 0.2);
}
::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.3);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(148, 163, 184, 0.5);
}

@media (max-width: 768px) {
    .workspace {
        flex-direction: column;
    }
    .feed-sidebar {
        width: 100%;
        height: 35vh;
        border-right: none;
        border-bottom: 1px solid var(--border-color);
    }
}
```

**Step 3: Commit styling and HTML changes**
```bash
git add static/styles.css
git commit -am "feat: create responsive dashboard HTML templates and dark styling"
```

---

### Task 5: Client-Side State & Feed Fetching

**Files:**
- Create: `static/app.js`

**Step 1: Write state management and fetch functions**
Create `static/app.js` with initialization logic:
```javascript
// State
let releases = [];
let activeFilter = 'ALL';
let searchQuery = '';
let selectedReleaseId = null;

// DOM Elements
const feedList = document.getElementById('feed-list');
const detailPane = document.getElementById('detail-pane');
const searchInput = document.getElementById('search-input');
const filtersContainer = document.getElementById('filters-container');
const refreshBtn = document.getElementById('refresh-btn');
const refreshIcon = document.getElementById('refresh-icon');

// Fetch Releases
async function fetchReleases(force = false) {
    setLoadingState(true);
    try {
        const url = force ? '/api/releases?refresh=true' : '/api/releases';
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load releases');
        
        releases = await response.json();
        renderList();
        
        // Auto-select first item if none is selected
        if (releases.length > 0 && !selectedReleaseId) {
            selectRelease(releases[0].id);
        }
    } catch (error) {
        feedList.innerHTML = `<div class="error-state">Error: ${error.message}</div>`;
    } finally {
        setLoadingState(false);
    }
}

function setLoadingState(isLoading) {
    if (isLoading) {
        refreshIcon.classList.add('spinning');
        refreshBtn.disabled = true;
    } else {
        refreshIcon.classList.remove('spinning');
        refreshBtn.disabled = false;
    }
}
```

**Step 2: Commit base app.js script**
```bash
git add static/app.js
git commit -m "feat: add app.js with AJAX fetching and spinner loading controls"
```

---

### Task 6: Search & Category Filtering

**Files:**
- Modify: `static/app.js`

**Step 1: Implement Render & Filter Logic**
Add filter handlers, search input binding, and render logic to `static/app.js`:
```javascript
// Render Sidebar Cards
function renderList() {
    // Filter and Search items
    const filtered = releases.filter(item => {
        const matchesCategory = activeFilter === 'ALL' || item.type === activeFilter;
        
        const cleanContent = stripHtml(item.content).toLowerCase();
        const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                              cleanContent.includes(searchQuery.toLowerCase());
                              
        return matchesCategory && matchesSearch;
    });

    if (filtered.length === 0) {
        feedList.innerHTML = '<div class="empty-state"><p>No release notes match your criteria.</p></div>';
        return;
    }

    feedList.innerHTML = filtered.map(item => {
        const isSelected = item.id === selectedReleaseId;
        const snippet = stripHtml(item.content);
        
        return `
            <div class="release-card ${isSelected ? 'active' : ''}" onclick="selectRelease('${item.id}')">
                <div class="card-header">
                    <span class="badge ${item.type}">${item.type}</span>
                    <span class="card-date">${item.date}</span>
                </div>
                <h3>${item.title}</h3>
                <p class="card-snippet">${snippet}</p>
            </div>
        `;
    }).join('');
}

// Helpers
function stripHtml(html) {
    const tmp = document.createElement("DIV");
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || "";
}

// Event Bindings
searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    renderList();
});

filtersContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('filter-badge')) {
        // Toggle Active Class
        document.querySelectorAll('.filter-badge').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        
        activeFilter = e.target.getAttribute('data-filter');
        renderList();
    }
});

refreshBtn.addEventListener('click', () => {
    fetchReleases(true);
});

// Init
document.addEventListener('DOMContentLoaded', () => {
    fetchReleases();
});
```

**Step 2: Verify Search and Category Badges**
Start server, type a keyword in the search bar, and verify notes filter in real time. Click different categories (Features, Deprecations) and verify selection matches.

**Step 3: Commit search and filter code**
```bash
git commit -am "feat: implement realtime search input and category filter badges in UI"
```

---

### Task 7: Details Display & Twitter Intent

**Files:**
- Modify: `static/app.js`

**Step 1: Write Select and Twitter Intent logic**
Implement `selectRelease` and `shareTweet` in `static/app.js`:
```javascript
function selectRelease(id) {
    selectedReleaseId = id;
    
    // Highlight active card
    document.querySelectorAll('.release-card').forEach(card => {
        card.classList.remove('active');
    });
    
    // Find item
    const item = releases.find(r => r.id === id);
    if (!item) return;
    
    // Render details
    detailPane.innerHTML = `
        <div class="detail-header">
            <div>
                <div class="detail-meta">
                    <span class="badge ${item.type}">${item.type}</span>
                    <span class="card-date">Published on ${item.date}</span>
                </div>
                <h2 class="detail-title">${item.title}</h2>
            </div>
            <button class="tweet-btn" onclick="shareTweet('${item.id}')">
                <svg viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                <span>Tweet</span>
            </button>
        </div>
        <div class="detail-content">
            ${item.content}
        </div>
    `;
    
    // Update sidebar active selection CSS class locally without re-rendering everything
    renderList();
}

function shareTweet(id) {
    const item = releases.find(r => r.id === id);
    if (!item) return;
    
    // Build tweet text
    const textSnippet = stripHtml(item.content).substring(0, 150) + "...";
    const tweetText = `BigQuery Update: ${item.title}\n\n"${textSnippet}"\n\n#GoogleCloud #BigQuery`;
    
    // Generate Twitter Web Intent URL
    const twitterIntentUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(tweetText)}`;
    
    // Open in a new tab
    window.open(twitterIntentUrl, '_blank', 'width=550,height=420');
}
```

**Step 2: Verify the whole dashboard integration**
1. Load `http://127.0.0.1:5000`.
2. Click on a release note card on the left. Verify that the detailed content is populated on the right.
3. Click "Tweet". Verify a new popup or tab opens with Twitter/X web intent, containing prefilled title, excerpt, and hashtags.

**Step 3: Commit**
```bash
git commit -am "feat: implement detail viewer pane and twitter intent link generation"
```
