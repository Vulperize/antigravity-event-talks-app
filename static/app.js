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
            <div class="release-card ${isSelected ? 'active' : ''}" data-id="${escapeHtml(item.id)}">
                <div class="card-header">
                    <span class="badge ${escapeHtml(item.type)}">${escapeHtml(item.type)}</span>
                    <span class="card-date">${escapeHtml(item.date)}</span>
                </div>
                <h3>${escapeHtml(item.title)}</h3>
                <p class="card-snippet">${escapeHtml(snippet)}</p>
            </div>
        `;
    }).join('');
}

// Helpers
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function stripHtml(html) {
    if (!html) return '';
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return doc.body.textContent || "";
}

// Stub function for selectRelease
function selectRelease(id) {
    console.log("Selecting: " + id);
}

// Event Bindings
feedList.addEventListener('click', (e) => {
    const card = e.target.closest('.release-card');
    if (card) {
        const id = card.getAttribute('data-id');
        selectRelease(id);
    }
});

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

// Init
document.addEventListener('DOMContentLoaded', () => {
    fetchReleases();
    refreshBtn.addEventListener('click', () => fetchReleases(true));
});
