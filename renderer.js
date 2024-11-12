let currentResults = {};

// Initialize error handling for unhandled promises
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});

async function startScraping(tabId) {
    const tab = document.getElementById(tabId);
    const status = tab.querySelector('.status');
    const exportButton = tab.querySelector('.export-button');
    const textarea = tab.querySelector('textarea');
    const table = tab.querySelector('table tbody');
    const numProductsInput = tab.querySelector('input[type="number"]');
    
    // Clear previous results
    table.innerHTML = '';
    currentResults[tabId] = [];
    exportButton.disabled = true;

    // Get input data
    const keywords = textarea.value.trim().split('\n').filter(item => item.length > 0);
    const numProducts = numProductsInput ? parseInt(numProductsInput.value) : null;

    if (keywords.length === 0) {
        status.textContent = 'Please enter at least one item to scrape';
        return;
    }

    try {
        status.textContent = 'Starting scraping process...';

        // Remove previous event listeners if any exist
        window.electronAPI.onScrapingProgress((data) => {
            status.textContent = `Scraping ${data.keyword} (${data.current}/${data.total})`;
        });

        window.electronAPI.onScrapingResult((data) => {
            if (data.result) {
                const results = Array.isArray(data.result) ? data.result : [data.result];
                results.forEach(result => {
                    appendResultToTable(tabId, result);
                    if (!currentResults[tabId]) {
                        currentResults[tabId] = [];
                    }
                    currentResults[tabId].push(result);
                });
            }
        });

        window.electronAPI.onScrapingError((data) => {
            console.error('Scraping error:', data.message);
            if (data.keyword) {
                status.textContent = `Error scraping ${data.keyword}: ${data.message}`;
            } else {
                status.textContent = `Error: ${data.message}`;
            }
        });

        // Start scraping
        const results = await window.electronAPI.startScraping({
            type: tabId,
            keywords: keywords,
            numProducts: numProducts
        });

        status.textContent = `Completed scraping ${keywords.length} items`;
        exportButton.disabled = false;
        currentResults[tabId] = results;

    } catch (error) {
        status.textContent = `Error: ${error.message || 'Unknown error occurred'}`;
        console.error('Scraping error:', error);
    }
}

function appendResultToTable(tabId, result) {
    if (!result) return;

    const table = document.getElementById(tabId).querySelector('table tbody');
    const row = document.createElement('tr');

    try {
        switch(tabId) {
            case 'amazon-rank':
                row.innerHTML = `
                    <td>${result.rank || ''}</td>
                    <td>${result.asin || ''}</td>
                    <td>${escapeHtml(result.title) || ''}</td>
                    <td>${result.price || ''}</td>
                    <td>${result.rating || ''}</td>
                    <td>${result.reviews || ''}</td>
                    <td>${result.type || ''}</td>
                `;
                break;

            case 'flipkart-rank':
                row.innerHTML = `
                    <td>${result.rank || ''}</td>
                    <td>${result.product_id || ''}</td>
                    <td>${escapeHtml(result.title) || ''}</td>
                    <td>${result.price || ''}</td>
                    <td>${result.rating || ''}</td>
                    <td>${result.reviews || ''}</td>
                    <td>${result.sponsored || ''}</td>
                `;
                break;

            case 'amazon-product':
                row.innerHTML = `
                    <td>${result.ASIN || ''}</td>
                    <td>${escapeHtml(result.title) || ''}</td>
                    <td>${result.price || ''}</td>
                    <td>${result.rating || ''}</td>
                    <td>${result.reviews || ''}</td>
                    <td>${escapeHtml(result.BestSeller) || ''}</td>
                    <td>${result.In_Stock || ''}</td>
                    <td>${result.bought_last_month || ''}</td>
                `;
                break;

            case 'flipkart-product':
                row.innerHTML = `
                    <td>${result.product_id || ''}</td>
                    <td>${escapeHtml(result.title) || ''}</td>
                    <td>${result.price || ''}</td>
                    <td>${result.rating || ''}</td>
                    <td>${result.reviews || ''}</td>
                `;
                break;
        }

        table.appendChild(row);
    } catch (error) {
        console.error('Error appending result to table:', error);
        console.error('Result data:', result);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function exportData(tabId) {
    const tab = document.getElementById(tabId);
    const status = tab.querySelector('.status');

    if (!currentResults[tabId] || currentResults[tabId].length === 0) {
        status.textContent = 'No data to export';
        return;
    }

    try {
        status.textContent = 'Exporting data...';
        
        const platform = tabId.includes('amazon') ? 'Amazon' : 'Flipkart';
        
        const success = await window.electronAPI.exportData({
            results: currentResults[tabId],
            platform: platform
        });

        if (success) {
            status.textContent = 'Data exported successfully';
        } else {
            status.textContent = 'Export cancelled';
        }
    } catch (error) {
        status.textContent = `Export error: ${error.message || 'Unknown error occurred'}`;
        console.error('Export error:', error);
    }
}

function openTab(evt, tabId) {
    const tabContents = document.getElementsByClassName('tab-content');
    for (let content of tabContents) {
        content.classList.remove('active');
    }

    const tabButtons = document.getElementsByClassName('tab-button');
    for (let button of tabButtons) {
        button.classList.remove('active');
    }

    document.getElementById(tabId).classList.add('active');
    evt.currentTarget.classList.add('active');
}

// Initialize tooltips for long text
function initializeTooltips() {
    const cells = document.querySelectorAll('.results-table td');
    cells.forEach(cell => {
        if (cell.offsetWidth < cell.scrollWidth) {
            cell.title = cell.textContent;
        }
    });
}