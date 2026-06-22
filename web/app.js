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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
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
        const response = await fetch('/api/games');
        allGames = await response.json();
        renderLibrary(allGames);
    } catch (error) {
        console.error('Failed to load games list:', error);
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
        
        card.innerHTML = `
            <div class="card-thumbnail">
                <img src="${game.thumbnail}" onerror="this.src='/web/assets/default_thumb.png';">
            </div>
            <div class="card-content">
                <h4>${game.name}</h4>
                <div class="card-meta">
                    <span><i class="fa-solid fa-hard-drive"></i> ${game.size_mb} MB</span>
                    <span><i class="fa-solid fa-calendar-days"></i> ${game.date_added}</span>
                </div>
                <div class="card-actions">
                    <button class="btn-play" onclick="playGame('${game.url}', '${game.name.replace(/'/g, "\\'")}')">
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
        const response = await fetch(`/api/download?url=${encodeURIComponent(url)}`);
        const result = await response.json();
        
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
        alert('Network error trying to connect to download API.');
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
            const response = await fetch(`/api/status?task_id=${taskId}`);
            const status = await response.json();
            
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
        const response = await fetch(`/api/delete?slug=${slug}`);
        const result = await response.json();
        if (result.success) {
            loadLibrary();
        } else {
            alert('Failed to delete game from directory.');
        }
    } catch (error) {
        alert('Network error trying to delete game.');
    }
}
