import os
import re
import json
import uuid
import shutil
import datetime
import threading
import urllib.parse
import http.server
import socketserver
import requests

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
GAMES_DIR = os.path.join(BASE_DIR, "games")
METADATA_FILE = os.path.join(BASE_DIR, "games_metadata.json")

os.makedirs(WEB_DIR, exist_ok=True)
os.makedirs(GAMES_DIR, exist_ok=True)

# State Management
download_tasks = {}
download_tasks_lock = threading.Lock()
metadata_lock = threading.Lock()

# Helpers
def get_current_date():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def get_games_list():
    with metadata_lock:
        if not os.path.exists(METADATA_FILE):
            return []
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("games", [])
        except Exception:
            return []

def add_game_to_metadata(game_info):
    with metadata_lock:
        data = {"games": []}
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                pass
        
        # Remove if already exists (overwrite)
        data["games"] = [g for g in data.get("games", []) if g["slug"] != game_info["slug"]]
        data["games"].append(game_info)
        
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

def delete_game(slug):
    with metadata_lock:
        # Delete folder
        game_dir = os.path.join(GAMES_DIR, slug)
        if os.path.exists(game_dir):
            try:
                shutil.rmtree(game_dir)
            except Exception as e:
                print(f"Error deleting folder {game_dir}: {e}")
                
        # Update metadata
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                data["games"] = [g for g in data.get("games", []) if g["slug"] != slug]
                with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                print(f"Error updating metadata: {e}")
        return False

# Logging for task
def log_task(task_id, message):
    with download_tasks_lock:
        if task_id in download_tasks:
            download_tasks[task_id]["logs"].append(message)
            print(f"[{task_id}] {message}")

def update_progress(task_id, progress):
    with download_tasks_lock:
        if task_id in download_tasks:
            download_tasks[task_id]["progress"] = progress

# Downloader Helper
def download_file(url, local_path, referer=None):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    if referer:
        headers["Referer"] = referer
    else:
        headers["Referer"] = "https://games.crazygames.com/"
        
    try:
        r = requests.get(url, headers=headers, stream=True, timeout=20)
        if r.status_code == 200:
            if local_path.endswith(('.br', '.gz')):
                r.raw.decode_content = False
                with open(local_path, 'wb') as f:
                    while True:
                        chunk = r.raw.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            else:
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True
        else:
            print(f"Failed download {url} (Status: {r.status_code})")
    except Exception as e:
        print(f"Error downloading {url}: {e}")
    return False

# Download Thread Task
def run_download_task(task_id, game_page_url):
    try:
        log_task(task_id, "Initializing downloader...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # 1. Fetch game page
        log_task(task_id, f"Fetching CrazyGames page: {game_page_url}")
        r = requests.get(game_page_url, headers=headers)
        if r.status_code != 200:
            log_task(task_id, f"Error: Failed to fetch game page (Status: {r.status_code})")
            with download_tasks_lock:
                download_tasks[task_id]["status"] = "failed"
            return
            
        # 2. Parse NEXT_DATA
        log_task(task_id, "Parsing page metadata...")
        match_next = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
        if not match_next:
            log_task(task_id, "Error: Could not parse page metadata (__NEXT_DATA__ tag missing)")
            with download_tasks_lock:
                download_tasks[task_id]["status"] = "failed"
            return
            
        data = json.loads(match_next.group(1))
        game_data = data.get("props", {}).get("pageProps", {}).get("game", {})
        
        game_name = game_data.get("name", "Unknown Game")
        game_slug = game_data.get("slug", "unknown-game")
        desktop_url = game_data.get("desktopUrl") or game_data.get("gameUrl") or game_data.get("url")
        cover_path = game_data.get("cover")
        
        with download_tasks_lock:
            download_tasks[task_id]["game_name"] = game_name
            download_tasks[task_id]["slug"] = game_slug
            
        log_task(task_id, f"Found game: '{game_name}' (slug: {game_slug})")
        
        if not desktop_url:
            log_task(task_id, "Error: Desktop launcher URL not found in page data.")
            with download_tasks_lock:
                download_tasks[task_id]["status"] = "failed"
            return
            
        # Create game folder
        game_dir = os.path.join(GAMES_DIR, game_slug)
        os.makedirs(game_dir, exist_ok=True)
        
        # 3. Download Thumbnail
        thumbnail_local_path = None
        if cover_path:
            thumbnail_url = f"https://images.crazygames.com/{cover_path}"
            log_task(task_id, "Downloading thumbnail image...")
            thumb_ext = "jpg"
            thumb_filename = f"thumbnail.{thumb_ext}"
            thumb_dest = os.path.join(game_dir, thumb_filename)
            if download_file(thumbnail_url, thumb_dest):
                thumbnail_local_path = f"/games/{game_slug}/{thumb_filename}"
                log_task(task_id, "Thumbnail downloaded successfully.")
            else:
                log_task(task_id, "Warning: Failed to download thumbnail.")
        
        # 4. Fetch launcher wrapper
        log_task(task_id, "Fetching game frame launcher wrapper...")
        r_desktop = requests.get(desktop_url, headers=headers)
        if r_desktop.status_code != 200:
            log_task(task_id, f"Error: Failed to fetch game launcher wrapper (Status: {r_desktop.status_code})")
            with download_tasks_lock:
                download_tasks[task_id]["status"] = "failed"
            return
            
        # 5. Extract the real game index HTML
        real_game_url = None
        match_loader = re.search(r'"loaderOptions"\s*:\s*\{\s*"url"\s*:\s*"([^"]+)"', r_desktop.text)
        if match_loader:
            real_game_url = match_loader.group(1)
            log_task(task_id, f"Found real game build entry: {real_game_url}")
        else:
            # Check if desktopUrl contains game canvas itself
            if "unity" in r_desktop.text or "canvas" in r_desktop.text or "<iframe" not in r_desktop.text:
                real_game_url = desktop_url
                log_task(task_id, "Launcher wrapper is the game itself.")
            else:
                log_task(task_id, "Error: Could not extract game build URL from launcher wrapper.")
                with download_tasks_lock:
                    download_tasks[task_id]["status"] = "failed"
                return
                
        # 6. Crawl game assets
        # Find base url directory
        if real_game_url.endswith('.html'):
            game_base_url = real_game_url.rsplit('/', 1)[0] + '/'
        else:
            game_base_url = real_game_url.rsplit('/', 1)[0] + '/'
            
        log_task(task_id, f"Game Base CDN URL: {game_base_url}")
        
        # Queue-based download crawler
        queue = [(real_game_url, None, 0)]
        queued = {real_game_url}
        
        total_files = 1
        completed_files = 0
        
        while queue:
            current_url, referrer, depth = queue.pop(0)
            file_name = current_url.split('/')[-1].split('?')[0] or "index.html"
            
            # Determine local path relative to game folder
            if current_url.startswith(game_base_url):
                rel_path = current_url[len(game_base_url):].split('?')[0]
                if not rel_path or rel_path == 'index.html':
                    rel_path = 'index.html'
            else:
                parsed = urllib.parse.urlparse(current_url)
                if "crazygames" in parsed.netloc:
                    rel_path = os.path.join("external", parsed.netloc, parsed.path.lstrip("/")).split('?')[0]
                else:
                    completed_files += 1
                    continue
                    
            local_path = os.path.join(game_dir, rel_path)
            
            log_task(task_id, f"Downloading [{completed_files + 1}/{total_files}]: {rel_path}...")
            
            # Download file
            success = download_file(current_url, local_path, referer=referrer)
            completed_files += 1
            
            if success:
                # Scan for more links if we are within depth limit and it's a parsed file type
                if depth < 2 and (local_path.endswith(('.html', '.js', '.css', '.json')) or 'index.html' in rel_path):
                    try:
                        with open(local_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                        found_links = []
                        # HTML tags
                        if local_path.endswith('.html') or 'index.html' in rel_path:
                            found_links.extend(re.findall(r'src=["\']([^"\']+)["\']', content))
                            found_links.extend(re.findall(r'href=["\']([^"\']+)["\']', content))
                        
                        # CSS urls
                        found_links.extend(re.findall(r'url\([\'"]?([^\)]+?)[\'"]?\)', content))
                        
                        # JS strings with standard asset extensions
                        found_links.extend(re.findall(r'(?:"|\'|`)([^"\'`\s]+?\.(?:js|css|wasm|data|json|png|jpg|jpeg|gif|br|unityweb|svg|mp4|mp3|ogg|wav))(?:"|\'|`)', content))
                        
                        # JS variable definitions and concatenations (e.g. buildUrl + "/filename.js")
                        if local_path.endswith(('.html', '.js')) or 'index.html' in rel_path:
                            variables = {}
                            # Find variable definitions: const/let/var name = "value"; or name = "value";
                            for match in re.finditer(r'(?:const|let|var)?\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*["\'`]([^"\'`\s]+)["\'`]', content):
                                var_name, var_val = match.groups()
                                variables[var_name] = var_val

                            # Also find object properties in config: propertyName: "value"
                            for match in re.finditer(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:\s*["\'`]([^"\'`\s]+)["\'`]', content):
                                var_name, var_val = match.groups()
                                variables[var_name] = var_val

                            # Find variable concatenation patterns like: buildUrl + "/..."
                            for match in re.finditer(r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\+\s*["\'`]([^"\'`\s]+)["\'`]', content):
                                var_name, suffix = match.groups()
                                if var_name in variables:
                                    prefix = variables[var_name]
                                    combined = prefix.rstrip('/') + '/' + suffix.lstrip('/')
                                    found_links.append(combined)

                            # Find string literal concatenations like: "Build" + "/..."
                            for match in re.finditer(r'["\'`]([^"\'`\s]+)["\'`]\s*\+\s*["\'`]([^"\'`\s]+)["\'`]', content):
                                prefix, suffix = match.groups()
                                combined = prefix.rstrip('/') + '/' + suffix.lstrip('/')
                                found_links.append(combined)

                        
                        # Process links
                        for link in found_links:
                            link = link.strip()
                            if not link or link.startswith(('data:', 'javascript:', 'blob:', 'mailto:', '#')):
                                continue
                            resolved_link = urllib.parse.urljoin(current_url, link)
                            
                            # Standardize URL
                            parsed_link = urllib.parse.urlparse(resolved_link)
                            
                            if resolved_link not in queued:
                                # We only crawl links that belong to the game base URL or crazygames assets
                                if resolved_link.startswith(game_base_url) or "crazygames" in parsed_link.netloc:
                                    queue.append((resolved_link, current_url, depth + 1))
                                    queued.add(resolved_link)
                                    total_files += 1
                                    
                    except Exception as e:
                        log_task(task_id, f"Warning: Failed to parse references in {rel_path} ({e})")
            else:
                log_task(task_id, f"Warning: Failed to download asset: {rel_path}")
                
            # Update progress status
            progress_pct = int((completed_files / total_files) * 98)
            update_progress(task_id, progress_pct)
            
        log_task(task_id, "Finalizing package details...")
        
        # Calculate folder size
        total_bytes = 0
        for root, dirs, files in os.walk(game_dir):
            for file in files:
                total_bytes += os.path.getsize(os.path.join(root, file))
        size_mb = round(total_bytes / (1024 * 1024), 2)
        
        # Add to local games metadata
        add_game_to_metadata({
            "slug": game_slug,
            "name": game_name,
            "thumbnail": thumbnail_local_path or "/web/assets/default_thumb.png",
            "url": f"/games/{game_slug}/index.html",
            "size_mb": size_mb,
            "date_added": get_current_date()
        })
        
        log_task(task_id, f"Game downloaded successfully! Total size: {size_mb} MB")
        update_progress(task_id, 100)
        with download_tasks_lock:
            download_tasks[task_id]["status"] = "completed"
            
    except Exception as e:
        log_task(task_id, f"Error: Scraper encountered an unhandled exception: {str(e)}")
        with download_tasks_lock:
            download_tasks[task_id]["status"] = "failed"

# Custom HTTP Request Handler
class ArcadeBoxRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        path_str = parsed.path
        
        if path_str.startswith('/games/'):
            rel = path_str[7:]
            return os.path.join(GAMES_DIR, rel)
        elif path_str.startswith('/api/'):
            return super().translate_path(path)
        else:
            rel = path_str.lstrip('/')
            if not rel:
                rel = 'index.html'
            return os.path.join(WEB_DIR, rel)
            
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        
        # API Routes
        if path == '/api/games':
            self.send_json_response(get_games_list())
            
        elif path == '/api/download':
            url = query.get('url', [None])[0]
            if not url:
                self.send_json_response({"error": "URL is required"}, 400)
                return
                
            # Create a background thread for the crawl task
            task_id = uuid.uuid4().hex[:12]
            with download_tasks_lock:
                download_tasks[task_id] = {
                    "status": "downloading",
                    "progress": 0,
                    "logs": [],
                    "game_name": "Parsing game metadata...",
                    "slug": ""
                }
                
            t = threading.Thread(target=run_download_task, args=(task_id, url))
            t.daemon = True
            t.start()
            
            self.send_json_response({"status": "started", "task_id": task_id})
            
        elif path == '/api/status':
            task_id = query.get('task_id', [None])[0]
            if not task_id:
                self.send_json_response({"error": "task_id is required"}, 400)
                return
                
            with download_tasks_lock:
                task = download_tasks.get(task_id)
                if not task:
                    self.send_json_response({"error": "Task not found"}, 404)
                    return
                self.send_json_response(task)
                
        elif path == '/api/delete':
            slug = query.get('slug', [None])[0]
            if not slug:
                self.send_json_response({"error": "slug is required"}, 400)
                return
                
            success = delete_game(slug)
            self.send_json_response({"success": success})
            
        else:
            # Fallback to serving static files
            super().do_GET()
            
    def send_json_response(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
        
    def end_headers(self):
        # Enable CORS
        self.send_header('Access-Control-Allow-Origin', '*')
        
        # Add custom headers for compressed game files (.br and .gz)
        if self.path.endswith('.br'):
            self.send_header('Content-Encoding', 'br')
            if '.wasm' in self.path:
                self.send_header('Content-Type', 'application/wasm')
            elif '.js' in self.path:
                self.send_header('Content-Type', 'application/javascript')
            elif '.data' in self.path:
                self.send_header('Content-Type', 'application/octet-stream')
        elif self.path.endswith('.gz'):
            self.send_header('Content-Encoding', 'gzip')
            if '.wasm' in self.path:
                self.send_header('Content-Type', 'application/wasm')
            elif '.js' in self.path:
                self.send_header('Content-Type', 'application/javascript')
            elif '.data' in self.path:
                self.send_header('Content-Type', 'application/octet-stream')
                
        super().end_headers()

# Start Server
def main():
    PORTS = [8000, 8080, 8888, 5000, 3000]
    httpd = None
    selected_port = None
    
    # Allow port reuse to prevent address already in use errors on rapid restarts
    socketserver.TCPServer.allow_reuse_address = True
    
    for port in PORTS:
        try:
            httpd = socketserver.TCPServer(("", port), ArcadeBoxRequestHandler)
            selected_port = port
            break
        except (OSError, PermissionError) as e:
            print(f"Port {port} is unavailable: {e}. Trying next...")
            continue
            
    if not httpd:
        try:
            # Bind to 0 to let OS select any free port
            httpd = socketserver.TCPServer(("", 0), ArcadeBoxRequestHandler)
            selected_port = httpd.server_address[1]
        except Exception as e:
            print(f"Critical Error: Could not bind to any port: {e}")
            return
            
    print(f"==================================================")
    print(f"ArcadeBox server started successfully!")
    print(f"Open in browser: http://localhost:{selected_port}")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == "__main__":
    main()
