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
        
        // Pre-compute Stripped HTML
        releases.forEach(item => {
            item.strippedContent = stripHtml(item.content);
        });
        
        renderList();
        
        // Auto-select first item if none is selected
        if (releases.length > 0 && !selectedReleaseId) {
            selectRelease(releases[0].id);
        }
    } catch (error) {
        feedList.innerHTML = `<div class="error-state">Error: ${escapeHtml(error.message)}</div>`;
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

function getFilteredReleases() {
    return releases.filter(item => {
        const matchesCategory = activeFilter === 'ALL' || item.type === activeFilter;
        const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                              item.strippedContent.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesCategory && matchesSearch;
    });
}

// Render Sidebar Cards
function renderList() {
    // Filter and Search items
    const filtered = getFilteredReleases();

    if (filtered.length === 0) {
        feedList.innerHTML = '<div class="empty-state"><p>No release notes match your criteria.</p></div>';
        return;
    }

    feedList.innerHTML = filtered.map(item => {
        const isSelected = item.id === selectedReleaseId;
        const snippet = item.strippedContent;
        
        return `
            <div class="release-card ${isSelected ? 'active' : ''}" data-id="${escapeHtml(item.id)}">
                <div class="card-header">
                    <span class="badge ${escapeHtml(item.type)}">${escapeHtml(item.type)}</span>
                    <div class="card-meta">
                        <button class="copy-btn" title="Copy to clipboard">📋</button>
                        <span class="card-date">${escapeHtml(item.date)}</span>
                    </div>
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

function selectRelease(id) {
    selectedReleaseId = id;
    
    // Highlight active card
    document.querySelectorAll('.release-card').forEach(card => {
        card.classList.remove('active');
    });
    
    const selectedCard = document.querySelector(`.release-card[data-id="${CSS.escape(id)}"]`);
    if (selectedCard) {
        selectedCard.classList.add('active');
    }
    
    // Find item
    const item = releases.find(r => r.id === id);
    if (!item) return;
    
    // Render details
    // Note: item.content contains parsed HTML, so we render it as-is in detail-content (no escapeHtml on item.content itself, but do escape the title and date).
    detailPane.innerHTML = `
        <div class="detail-header">
            <div>
                <div class="detail-meta">
                    <span class="badge ${escapeHtml(item.type)}">${escapeHtml(item.type)}</span>
                    <span class="card-date">Published on ${escapeHtml(item.date)}</span>
                </div>
                <h2 class="detail-title">${escapeHtml(item.title)}</h2>
            </div>
            <button class="tweet-btn" data-id="${escapeHtml(item.id)}">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
                <span>Tweet</span>
            </button>
        </div>
        <div class="detail-content">
            ${item.content}
        </div>
    `;
}

function shareTweet(id) {
    const item = releases.find(r => r.id === id);
    if (!item) return;
    
    // Build tweet text
    const textSnippet = item.strippedContent.length > 150 ? 
        item.strippedContent.substring(0, 150) + "..." : 
        item.strippedContent;
    const tweetText = `BigQuery Update: ${item.title}\n\n"${textSnippet}"\n\n#GoogleCloud #BigQuery`;
    
    // Generate Twitter Web Intent URL
    const twitterIntentUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(tweetText)}`;
    
    // Open in a new tab
    window.open(twitterIntentUrl, '_blank', 'width=550,height=420');
}

// Event Bindings
detailPane.addEventListener('click', (e) => {
    const btn = e.target.closest('.tweet-btn');
    if (btn) {
        const id = btn.getAttribute('data-id');
        shareTweet(id);
    }
});

async function copyToClipboard(btn, text) {
    try {
        await navigator.clipboard.writeText(text);
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '✓';
        setTimeout(() => { btn.innerHTML = originalHTML; }, 1500);
    } catch (err) {
        console.error('Failed to copy text: ', err);
    }
}

feedList.addEventListener('click', (e) => {
    const copyBtn = e.target.closest('.copy-btn');
    if (copyBtn) {
        e.stopPropagation(); // Stop click from selecting card
        const card = copyBtn.closest('.release-card');
        const id = card.getAttribute('data-id');
        const item = releases.find(r => r.id === id);
        if (item) {
            // Copy title and plain text snippet
            const snippet = item.strippedContent;
            copyToClipboard(copyBtn, `${item.title}: ${snippet}`);
        }
        return;
    }
    
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

    // Theme Switch
    const toggleSwitch = document.querySelector('.theme-switch input[type="checkbox"]');
    if (toggleSwitch) {
        toggleSwitch.addEventListener('change', (e) => {
            if (e.target.checked) {
                document.body.classList.add('light-mode');
            } else {
                document.body.classList.remove('light-mode');
            }
        });
    }

    // CSV Export
    const exportBtn = document.getElementById('export-csv-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            // Generate CSV from currently active (filtered/searched) release notes
            const filtered = getFilteredReleases();
            
            let csvContent = "ID,Date,Category,Title,Content\n";
            filtered.forEach(item => {
                const row = [
                    item.id,
                    item.date,
                    item.type,
                    `"${item.title.replace(/"/g, '""')}"`,
                    `"${item.strippedContent.replace(/"/g, '""').replace(/\n/g, ' ')}"`
                ].join(",");
                csvContent += row + "\n";
            });
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `bigquery_releases_${activeFilter.toLowerCase()}.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        });
    }
});
