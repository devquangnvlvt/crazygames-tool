// DOM Elements
const downloadForm = document.getElementById('download-form');
const gameUrlInput = document.getElementById('game-url');
const downloadBtn = document.getElementById('download-btn');
const activeDownloadSection = document.getElementById('active-download-section');
const downloadGameTitle = document.getElementById('download-game-title');
const downloadPercentage = document.getElementById('download-percentage');
const progressBar = document.getElementById('progress-bar');
const consoleLogs = document.getElementById('console-logs');
const toggleConsoleBtn = document.getElementById('toggle-console');
const gamesGrid = document.getElementById('games-grid');
const noGamesView = document.getElementById('no-games-view');
const librarySearch = document.getElementById('library-search');

// Modal Elements
const playerModal = document.getElementById('player-modal');
const modalGameTitle = document.getElementById('modal-game-title');
const gameIframe = document.getElementById('game-iframe');
const closeModalBtn = document.getElementById('close-modal-btn');
const fullscreenGameBtn = document.getElementById('fullscreen-game-btn');

// State Variables
let currentTaskId = null;
let pollInterval = null;
let allGames = [];
let backendUrl = ''; // Auto-discovered backend host

// Backend Auto-Discovery for Cross-Origin / Live-Server setups
async function discoverBackend() {
    const ports = ['8000', '8080', '8888', '5000', '3000'];
    
    // If running directly on one of our backend ports, use relative URLs
    if (ports.includes(window.location.port)) {
        backendUrl = '';
        return;
    }
    
    // Try to locate the backend by sending small test requests to candidates
    for (const port of ports) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 200);
            const response = await fetch(`http://localhost:${port}/api/games`, { signal: controller.signal });
            clearTimeout(timeoutId);
            if (response.ok) {
                backendUrl = `http://localhost:${port}`;
                console.log(`Discovered ArcadeBox backend at: ${backendUrl}`);
                return;
            }
        } catch (err) {
            // Port not open or CORS failed, try next
        }
    }
    
    // If not found, log warning
    if (window.location.protocol.startsWith('http')) {
        console.warn('Could not connect to ArcadeBox server. Ensure server.py is running.');
    }
}

// Unified API caller with response verification
async function apiRequest(path) {
    const url = `${backendUrl}${path}`;
    try {
        const response = await fetch(url);
        if (!response.ok) {
            let errorMsg = `HTTP Error ${response.status}`;
            try {
                const errData = await response.json();
                if (errData && errData.error) errorMsg = errData.error;
            } catch (_) {}
            throw new Error(errorMsg);
        }
        return await response.json();
    } catch (error) {
        console.error(`API Request to ${url} failed:`, error);
        throw error;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Show a loading indicator inside the games grid while discovering backend
    gamesGrid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 3rem;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 2.5rem; color: var(--color-primary); margin-bottom: 1rem;"></i>
            <p style="color: var(--color-text-muted);">Connecting to ArcadeBox Backend...</p>
        </div>
    `;

    await discoverBackend();
    loadLibrary();
    
    // Toggle log console height/collapse
    toggleConsoleBtn.addEventListener('click', () => {
        if (consoleLogs.style.display === 'none') {
            consoleLogs.style.display = 'flex';
            toggleConsoleBtn.innerHTML = '<i class="fa-solid fa-chevron-down"></i>';
        } else {
            consoleLogs.style.display = 'none';
            toggleConsoleBtn.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';
        }
    });
});

// Load Games Library
async function loadLibrary() {
    try {
        allGames = await apiRequest('/api/games');
        renderLibrary(allGames);
    } catch (error) {
        console.error('Failed to load games list:', error);
        noGamesView.classList.add('hidden');
        gamesGrid.classList.remove('hidden');
        gamesGrid.innerHTML = `
            <div class="error-container" style="grid-column: 1/-1; text-align: center; padding: 2rem; background: rgba(244, 63, 94, 0.1); border: 1px solid var(--color-error); border-radius: var(--border-radius-md);">
                <i class="fa-solid fa-circle-exclamation" style="font-size: 2rem; color: var(--color-error); margin-bottom: 0.5rem;"></i>
                <h3 style="color: var(--color-error);">Connection Error</h3>
                <p style="color: var(--color-text-muted); font-size: 0.9rem; margin-top: 0.5rem;">
                    Could not connect to the ArcadeBox server. Make sure <code>python server.py</code> is running, then click the retry button.
                </p>
                <button onclick="loadLibrary()" style="margin-top: 1rem; background: var(--color-primary); box-shadow: 0 0 10px var(--color-primary-glow); border: none; color: white; padding: 0.5rem 1rem; border-radius: var(--border-radius-md); cursor: pointer; font-family: var(--font-sans); font-weight: 600; transition: var(--transition-smooth);">
                    <i class="fa-solid fa-rotate"></i> Retry Connection
                </button>
            </div>
        `;
    }
}

// Render library grid
function renderLibrary(games) {
    gamesGrid.innerHTML = '';
    
    if (games.length === 0) {
        noGamesView.classList.remove('hidden');
        gamesGrid.classList.add('hidden');
        return;
    }
    
    noGamesView.classList.add('hidden');
    gamesGrid.classList.remove('hidden');
    
    games.forEach(game => {
        const card = document.createElement('div');
        card.className = 'game-card';
        card.setAttribute('data-name', game.name.toLowerCase());
        
        // Handle local paths correctly if backendUrl is set
        const thumbnailSrc = game.thumbnail.startsWith('/') && backendUrl ? `${backendUrl}${game.thumbnail}` : game.thumbnail;
        const playUrl = game.url.startsWith('/') && backendUrl ? `${backendUrl}${game.url}` : game.url;
        
        card.innerHTML = `
            <div class="card-thumbnail">
                <img src="${thumbnailSrc}" onerror="this.src='assets/default_thumb.png';">
            </div>
            <div class="card-content">
                <h4>${game.name}</h4>
                <div class="card-meta">
                    <span><i class="fa-solid fa-hard-drive"></i> ${game.size_mb} MB</span>
                    <span><i class="fa-solid fa-calendar-days"></i> ${game.date_added}</span>
                </div>
                <div class="card-actions">
                    <button class="btn-play" onclick="playGame('${playUrl}', '${game.name.replace(/'/g, "\\'")}')">
                        <i class="fa-solid fa-circle-play"></i> Play Offline
                    </button>
                    <button class="btn-delete" onclick="deleteGame('${game.slug}', '${game.name.replace(/'/g, "\\'")}')" title="Delete Game">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </div>
        `;
        gamesGrid.appendChild(card);
    });
}

// Filter library based on search input
librarySearch.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const filtered = allGames.filter(game => game.name.toLowerCase().includes(query));
    renderLibrary(filtered);
});

// Download Submission Handler
downloadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = gameUrlInput.value.trim();
    if (!url) return;
    
    // Disable UI
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Triggering...';
    
    try {
        const result = await apiRequest(`/api/download?url=${encodeURIComponent(url)}`);
        
        if (result.status === 'started') {
            currentTaskId = result.task_id;
            
            // UI transitions
            activeDownloadSection.classList.remove('hidden');
            consoleLogs.innerHTML = '';
            appendLog('Connecting to downloader task...');
            progressBar.style.width = '0%';
            downloadPercentage.innerText = '0%';
            downloadGameTitle.innerText = 'Analyzing game page...';
            
            // Clear input field
            gameUrlInput.value = '';
            
            // Start progress polling
            startPolling(currentTaskId);
        } else {
            alert('Failed to start download: ' + (result.error || 'Unknown error'));
            resetDownloadButton();
        }
    } catch (error) {
        alert('Failed to start download: ' + error.message);
        resetDownloadButton();
    }
});

function resetDownloadButton() {
    downloadBtn.disabled = false;
    downloadBtn.innerHTML = '<i class="fa-solid fa-circle-down"></i> Download';
}

// Task Polling Loop
function startPolling(taskId) {
    if (pollInterval) clearInterval(pollInterval);
    
    pollInterval = setInterval(async () => {
        try {
            const status = await apiRequest(`/api/status?task_id=${taskId}`);
            
            if (status.error) {
                clearInterval(pollInterval);
                alert('Task monitoring error: ' + status.error);
                resetDownloadButton();
                return;
            }
            
            // Update Title, Progress, and Logs
            downloadGameTitle.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-primary"></i> ${status.game_name}`;
            downloadPercentage.innerText = `${status.progress}%`;
            progressBar.style.width = `${status.progress}%`;
            
            // Render logs difference
            renderLogs(status.logs);
            
            if (status.status === 'completed') {
                clearInterval(pollInterval);
                downloadGameTitle.innerHTML = `<i class="fa-solid fa-circle-check text-success"></i> ${status.game_name}`;
                appendLog('SUCCESS: Task wrapped up successfully.');
                resetDownloadButton();
                loadLibrary();
                
                // Hide download section after brief delay
                setTimeout(() => {
                    activeDownloadSection.classList.add('hidden');
                }, 4000);
            } else if (status.status === 'failed') {
                clearInterval(pollInterval);
                downloadGameTitle.innerHTML = `<i class="fa-solid fa-circle-exclamation text-error"></i> Download Failed`;
                appendLog('ERROR: Task execution terminated due to errors.');
                resetDownloadButton();
            }
        } catch (error) {
            console.error('Polling error:', error);
            appendLog(`WARNING: Connection lost to status API. Retrying... (${error.message})`);
        }
    }, 800);
}

// Render log buffer and auto scroll
let lastLogCount = 0;
function renderLogs(logs) {
    if (logs.length > lastLogCount) {
        for (let i = lastLogCount; i < logs.length; i++) {
            appendLog(logs[i]);
        }
        lastLogCount = logs.length;
    }
}

function appendLog(message) {
    const line = document.createElement('div');
    const timestamp = new Date().toLocaleTimeString();
    line.innerText = `[${timestamp}] ${message}`;
    consoleLogs.appendChild(line);
    consoleLogs.scrollTop = consoleLogs.scrollHeight;
}

// Play Game Action
function playGame(url, name) {
    modalGameTitle.innerText = name;
    gameIframe.src = url;
    playerModal.classList.remove('hidden');
}

// Close Game Action
closeModalBtn.addEventListener('click', () => {
    playerModal.classList.add('hidden');
    gameIframe.src = ''; // reset iframe to stop execution/sound
});

// Fullscreen execution trigger
fullscreenGameBtn.addEventListener('click', () => {
    if (gameIframe.requestFullscreen) {
        gameIframe.requestFullscreen();
    } else if (gameIframe.webkitRequestFullscreen) {
        gameIframe.webkitRequestFullscreen(); // Safari
    } else if (gameIframe.msRequestFullscreen) {
        gameIframe.msRequestFullscreen(); // IE11
    }
});

// Delete Game Action
async function deleteGame(slug, name) {
    const confirmed = confirm(`Are you sure you want to permanently delete '${name}'? This will free up local disk space.`);
    if (!confirmed) return;
    
    try {
        const result = await apiRequest(`/api/delete?slug=${slug}`);
        if (result.success) {
            loadLibrary();
        } else {
            alert('Failed to delete game from directory.');
        }
    } catch (error) {
        alert('Failed to delete game: ' + error.message);
    }
}
