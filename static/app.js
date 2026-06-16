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

// Stub function for selectRelease
function selectRelease(id) {
    console.log("Selecting: " + id);
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

// Init
document.addEventListener('DOMContentLoaded', () => {
    fetchReleases();
    refreshBtn.addEventListener('click', () => fetchReleases(true));
});
