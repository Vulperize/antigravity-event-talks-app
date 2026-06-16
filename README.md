# BigQuery Release Notes Dashboard

A modern, responsive single-page web application built with a **Python Flask** backend and a **vanilla HTML, CSS, and JavaScript** frontend. It fetches, parses, and displays Google Cloud's BigQuery release notes XML feed in a premium master-detail layout, allowing users to search, filter by category, and easily Tweet about specific updates.

## Features

- 🔄 **Real-time Refresh**: Pull the latest updates with a simple refresh button featuring an animated loading spinner.
- ⚡ **In-Memory Caching**: Server-side caching guarantees fast page loads and prevents hitting Google's rate limits.
- 🎨 **Premium UI/UX**: Responsive master-detail layout featuring a dark-themed glassmorphism design, custom fonts, hover micro-animations, and fluid transitions.
- 🔍 **Real-Time Search & Filtering**: Instantly search updates by keywords or filter by category badges (`FEATURE`, `CHANGE`, `DEPRECATION`, `BUGFIX`).
- 🐦 **Twitter/X Web Intent Integration**: Easily share updates on Twitter/X with pre-formatted templates opening in a new tab.

## Architecture

- **Backend (Flask)**: Fetches the XML feed from `https://docs.cloud.google.com/feeds/bigquery-release-notes.xml`, parses the entries, extracts types/categories, caches results in-memory, and serves the static assets and `/api/releases` API.
- **Frontend (Vanilla HTML/CSS/JS)**: Clean single-page application (SPA) with CSS variables for dynamic styling and asynchronous AJAX requests for loading and filtering notes.

## Quick Start

### 1. Prerequisites
Ensure you have Python 3.8+ and pip installed.

### 2. Installation
Clone the repository, navigate to the folder, and install dependencies:
```bash
pip install flask requests
```

### 3. Run the Server
Start the Flask development server:
```bash
python app.py
```

Open your browser and navigate to:
👉 **http://127.0.0.1:5000**
