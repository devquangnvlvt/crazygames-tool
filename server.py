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
import gzip
import brotli

# Decompression Helper for .br and .gz files
def decompress_file(src_path, dest_path):
    if src_path.endswith('.br'):
        try:
            with open(src_path, 'rb') as f_in:
                compressed_data = f_in.read()
            decompressed_data = brotli.decompress(compressed_data)
            with open(dest_path, 'wb') as f_out:
                f_out.write(decompressed_data)
            return True
        except Exception as e:
            print(f"Brotli decompression failed: {e}")
            return False
    elif src_path.endswith('.gz'):
        try:
            with gzip.open(src_path, 'rb') as f_in:
                with open(dest_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return True
        except Exception as e:
            print(f"Gzip decompression failed: {e}")
            return False
    else:
        try:
            shutil.copyfile(src_path, dest_path)
            return True
        except Exception as e:
            print(f"Copy failed: {e}")
            return False

# Template for generating beautiful, branding-free offline index.html
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{game_title}</title>
  <!-- Google Fonts for premium typography -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">

  <style>
    /* Reset and sleek styling */
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
    }}

    body,
    html {{
      width: 100%;
      height: 100%;
      overflow: hidden;
      background-color: #0b0c10;
      font-family: 'Outfit', sans-serif;
      color: #fff;
    }}

    /* Ambient background gradient with subtle pulse animation */
    .bg-animation {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 0;
      background: linear-gradient(135deg, #0f0c20 0%, #15102a 50%, #090615 100%);
      background-size: 400% 400%;
      animation: gradientBG 15s ease infinite;
    }}

    @keyframes gradientBG {{
      0% {{
        background-position: 0% 50%;
      }}

      50% {{
        background-position: 100% 50%;
      }}

      100% {{
        background-position: 0% 50%;
      }}
    }}

    /* Game Container */
    #game-container {{
      position: relative;
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1;
    }}

    #unity-canvas {{
      width: 100%;
      height: 100%;
      background: transparent;
      display: block;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
      transition: opacity 0.5s ease;
    }}

    /* Glassmorphic Loader HUD */
    #loader-hud {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      z-index: 10;
      background: rgba(11, 12, 16, 0.85);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      transition: opacity 0.8s cubic-bezier(0.25, 1, 0.5, 1);
    }}

    .loader-card {{
      width: 90%;
      max-width: 460px;
      padding: 40px;
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 30px 60px rgba(0, 0, 0, 0.4),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      animation: cardEntrance 1s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }}

    @keyframes cardEntrance {{
      from {{
        opacity: 0;
        transform: translateY(30px) scale(0.95);
      }}

      to {{
        opacity: 1;
        transform: translateY(0) scale(1);
      }}
    }}

    /* Modern Progress Bar */
    .progress-container {{
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 100px;
      overflow: hidden;
      margin-bottom: 16px;
      position: relative;
    }}

    .progress-bar {{
      width: 0%;
      height: 100%;
      background: linear-gradient(to right, #a855f7, #6366f1);
      border-radius: 100px;
      transition: width 0.3s ease;
      box-shadow: 0 0 10px rgba(168, 85, 247, 0.5);
    }}

    .loading-status {{
      font-size: 13px;
      color: #a855f7;
      font-weight: 600;
      letter-spacing: 0.5px;
    }}

    /* Responsive adjustments */
    @media (max-width: 480px) {{
      .loader-card {{
        padding: 30px 20px;
      }}
    }}
  </style>
</head>

<body>

  <!-- Ambient BG -->
  <div class="bg-animation"></div>

  <!-- Main Game Container -->
  <div id="game-container">
    <canvas id="unity-canvas"></canvas>
  </div>

  <!-- Glassmorphic Loader -->
  <div id="loader-hud">
    <div class="loader-card">
      <div class="progress-container">
        <div class="progress-bar" id="progress-bar"></div>
      </div>
      <div class="loading-status" id="loading-status">CHUẨN BỊ TÀI NGUYÊN... 0%</div>
    </div>
  </div>

  <!-- GamePush SDK Fallback & Interceptor: Register before Unity Loader to avoid race conditions -->
  <script>
    var _gpFallbackTimeout = setTimeout(function () {{
      // If SDK never triggered onGPInit, manually fire a stub to unblock the game
      if (typeof window.onGPInit === 'function' && typeof window.GamePush === 'undefined') {{
        console.warn('[Fallback] GamePush SDK did not load in time. Starting game without SDK.');

        // Create a minimal stub gp object so onGPInit doesn't throw
        var stubGp = {{
          ads: {{ showPreloader: function () {{}} }},
          player: {{ ready: Promise.resolve() }}
        }};
        window.onGPInit(stubGp);
      }}

      // Also directly unblock Unity if _UnityReady exists and hasn't been called yet
      if (typeof _UnityReady === 'function') {{
        try {{ _UnityReady(); }} catch (e) {{}}
      }}
    }}, 6000);

    // Cancel fallback if SDK loads successfully on its own
    var _origOnGPInit = window.onGPInit;
    Object.defineProperty(window, 'onGPInit', {{
      set: function (fn) {{
        _origOnGPInit = fn;
        // wrap to clear fallback timer on success
        window._realOnGPInit = function (gp) {{
          clearTimeout(_gpFallbackTimeout);

          if (gp) {{
            // Helper to patch methods using Object.defineProperty to bypass read-only/prototype constraints
            function patchMethod(obj, methodName, androidCallback, logValue) {{
              var originalMethod = obj[methodName];
              var newMethod = function () {{
                console.log(methodName + ' triggered with arguments:', arguments);
                if (window.AndroidBridge && typeof window.AndroidBridge[androidCallback] === 'function') {{
                  console.log('Sending ' + logValue + ' to Android Bridge');
                  window.AndroidBridge[androidCallback](logValue);
                }} else {{
                  console.log('AndroidBridge.' + androidCallback + ' is not available');
                }}
                if (typeof originalMethod === 'function') {{
                  return originalMethod.apply(this, arguments);
                }}
              }};

              try {{
                Object.defineProperty(obj, methodName, {{
                  value: newMethod,
                  writable: true,
                  configurable: true
                }});
                console.log('Successfully patched ' + methodName + ' via defineProperty');
              }} catch (e) {{
                console.warn('Failed to defineProperty for ' + methodName + ', using direct assignment:', e);
                obj[methodName] = newMethod;
              }}
            }}

            patchMethod(gp, 'gameplayStart', 'onGameplayStart', 'start_gameplay');
            patchMethod(gp, 'gameplayStop', 'onGameplayStop', 'stop_gameplay');
          }}

          return fn(gp);
        }};
      }},
      get: function () {{
        return window._realOnGPInit || _origOnGPInit;
      }},
      configurable: true
    }});
  </script>

  <!-- Unity WebGL Bootloader -->
  <script src="{loader_script}"></script>

  <script>
    if (window.AndroidBridge) {{
      // window.AndroidBridge.onGoHome(true); 
    }} else {{
      console.log("Không chạy trên ứng dụng Android.");
    }}
  </script>

  <script>
    const canvas = document.querySelector("#unity-canvas");
    const loaderHUD = document.querySelector("#loader-hud");
    const progressBar = document.querySelector("#progress-bar");
    const loadingStatus = document.querySelector("#loading-status");

    let myUnityInstance = null;

    // Load configurations pointing to uncompressed local files
    createUnityInstance(canvas, {{
      dataUrl: "Build/data.data",
      frameworkUrl: "Build/framework.js",
      codeUrl: "Build/code.wasm",
      streamingAssetsUrl: "Build/StreamingAssets",
      companyName: "{company_name}",
      productName: "{product_name}",
      productVersion: "{product_version}",
    }}, (progress) => {{
      const percentage = Math.round(progress * 100);
      progressBar.style.width = `${{percentage}}%`;
      loadingStatus.textContent = `ĐANG TẢI TÀI NGUYÊN... ${{percentage}}%`;
    }}).then((unityInstance) => {{
      myUnityInstance = unityInstance;
      // Fade out loading HUD smoothly
      loaderHUD.style.opacity = "0";
      setTimeout(() => {{
        loaderHUD.style.display = "none";
      }}, 800);
    }}).catch((message) => {{
      loadingStatus.textContent = "CÓ LỖI XẢY RA KHI TẢI GAME!";
      loadingStatus.style.color = "#ef4444";
      console.error(message);
    }});

  </script>
</body>

</html>"""

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
            
        # 5. Check if it's a Unity WebGL game
        log_task(task_id, "Analyzing launcher configuration...")
        
        # Search for unityLoaderUrl and other configs
        unity_loader_match = re.search(r'["\']?unityLoaderUrl["\']?\s*:\s*["\']([^"\']+)["\']', r_desktop.text)
        if not unity_loader_match:
            # Fallback: search for loaderUrl var
            unity_loader_match = re.search(r'(?:const|let|var)\s+loaderUrl\s*=\s*(?:buildUrl\s*\+\s*)?["\']([^"\']+)["\']', r_desktop.text)
            if not unity_loader_match:
                unity_loader_match = re.search(r'["\']([^"\']+\.loader\.js[^"\']*)["\']', r_desktop.text)

        is_unity_webgl = False
        loader_url = None
        code_url = None
        data_url = None
        framework_url = None
        streaming_assets_url = None

        if unity_loader_match:
            loader_url = urllib.parse.urljoin(desktop_url, unity_loader_match.group(1))
            
            # Find the other files
            code_match = re.search(r'["\']?codeUrl["\']?\s*:\s*(?:buildUrl\s*\+\s*)?["\']([^"\']+)["\']', r_desktop.text)
            if not code_match:
                code_match = re.search(r'["\']([^"\']+\.wasm(?:\.br|\.gz)?(?:[^"\']*)?)["\']', r_desktop.text)
            if code_match:
                code_url = urllib.parse.urljoin(desktop_url, code_match.group(1))

            data_match = re.search(r'["\']?dataUrl["\']?\s*:\s*(?:buildUrl\s*\+\s*)?["\']([^"\']+)["\']', r_desktop.text)
            if not data_match:
                data_match = re.search(r'["\']([^"\']+\.data(?:\.br|\.gz)?(?:[^"\']*)?)["\']', r_desktop.text)
            if data_match:
                data_url = urllib.parse.urljoin(desktop_url, data_match.group(1))

            framework_match = re.search(r'["\']?frameworkUrl["\']?\s*:\s*(?:buildUrl\s*\+\s*)?["\']([^"\']+)["\']', r_desktop.text)
            if not framework_match:
                framework_match = re.search(r'["\']([^"\']+\.framework\.js(?:\.br|\.gz)?(?:[^"\']*)?)["\']', r_desktop.text)
                if not framework_match:
                    framework_match = re.search(r'["\']([^"\']+\.js(?:\.br|\.gz)?(?:[^"\']*)?)["\']', r_desktop.text)
            if framework_match:
                framework_url = urllib.parse.urljoin(desktop_url, framework_match.group(1))

            streaming_match = re.search(r'["\']?streamingAssetsUrl["\']?\s*:\s*["\']([^"\']+)["\']', r_desktop.text)
            if streaming_match:
                streaming_assets_url = urllib.parse.urljoin(desktop_url, streaming_match.group(1))

            if loader_url and code_url and data_url and framework_url:
                is_unity_webgl = True

        if is_unity_webgl:
            log_task(task_id, "Detected Unity WebGL. Commencing clean extraction mode...")
            
            # Create Build directory
            build_dir = os.path.join(game_dir, "Build")
            os.makedirs(build_dir, exist_ok=True)
            os.makedirs(os.path.join(build_dir, "StreamingAssets"), exist_ok=True)
            
            # Set up file paths
            loader_filename = loader_url.split('/')[-1].split('?')[0]
            local_loader_path = os.path.join(build_dir, loader_filename)
            local_code_path = os.path.join(build_dir, "code.wasm")
            local_data_path = os.path.join(build_dir, "data.data")
            local_framework_path = os.path.join(build_dir, "framework.js")
            
            # 1. Download Loader
            update_progress(task_id, 20)
            log_task(task_id, f"Downloading Unity Loader JS: {loader_filename}...")
            if not download_file(loader_url, local_loader_path):
                log_task(task_id, "Error: Failed to download Unity Loader.")
                with download_tasks_lock:
                    download_tasks[task_id]["status"] = "failed"
                return
                
            # 2. Download and decompress WASM
            update_progress(task_id, 45)
            log_task(task_id, "Downloading and decompressing WebAssembly...")
            code_temp = local_code_path
            is_br = code_url.endswith('.br') or '.br' in code_url
            is_gz = code_url.endswith('.gz') or '.gz' in code_url
            if is_br:
                code_temp = local_code_path + '.br'
            elif is_gz:
                code_temp = local_code_path + '.gz'
                
            if not download_file(code_url, code_temp):
                log_task(task_id, "Error: Failed to download WASM code file.")
                with download_tasks_lock:
                    download_tasks[task_id]["status"] = "failed"
                return
                
            if is_br or is_gz:
                if not decompress_file(code_temp, local_code_path):
                    log_task(task_id, "Error: Failed to decompress WebAssembly file.")
                    with download_tasks_lock:
                        download_tasks[task_id]["status"] = "failed"
                    return
                try:
                    os.remove(code_temp)
                except Exception:
                    pass
            
            # 3. Download and decompress Data
            update_progress(task_id, 70)
            log_task(task_id, "Downloading and decompressing Game Data...")
            data_temp = local_data_path
            is_br = data_url.endswith('.br') or '.br' in data_url
            is_gz = data_url.endswith('.gz') or '.gz' in data_url
            if is_br:
                data_temp = local_data_path + '.br'
            elif is_gz:
                data_temp = local_data_path + '.gz'
                
            if not download_file(data_url, data_temp):
                log_task(task_id, "Error: Failed to download game data file.")
                with download_tasks_lock:
                    download_tasks[task_id]["status"] = "failed"
                return
                
            if is_br or is_gz:
                if not decompress_file(data_temp, local_data_path):
                    log_task(task_id, "Error: Failed to decompress game data file.")
                    with download_tasks_lock:
                        download_tasks[task_id]["status"] = "failed"
                    return
                try:
                    os.remove(data_temp)
                except Exception:
                    pass
            
            # 4. Download and decompress Framework
            update_progress(task_id, 90)
            log_task(task_id, "Downloading and decompressing Framework JS...")
            fw_temp = local_framework_path
            is_br = framework_url.endswith('.br') or '.br' in framework_url
            is_gz = framework_url.endswith('.gz') or '.gz' in framework_url
            if is_br:
                fw_temp = local_framework_path + '.br'
            elif is_gz:
                fw_temp = local_framework_path + '.gz'
                
            if not download_file(framework_url, fw_temp):
                log_task(task_id, "Error: Failed to download framework JS file.")
                with download_tasks_lock:
                    download_tasks[task_id]["status"] = "failed"
                return
                
            if is_br or is_gz:
                if not decompress_file(fw_temp, local_framework_path):
                    log_task(task_id, "Error: Failed to decompress framework JS file.")
                    with download_tasks_lock:
                        download_tasks[task_id]["status"] = "failed"
                    return
                try:
                    os.remove(fw_temp)
                except Exception:
                    pass

            # 5. Extract properties & Generate clean index.html
            update_progress(task_id, 95)
            log_task(task_id, "Generating beautiful loader index.html (No CrazyGames branding)...")
            
            company_name_match = re.search(r'companyName\s*:\s*["\']([^"\']+)["\']', r_desktop.text)
            company_name = company_name_match.group(1) if company_name_match else "DefaultCompany"

            product_name_match = re.search(r'productName\s*:\s*["\']([^"\']+)["\']', r_desktop.text)
            product_name = product_name_match.group(1) if product_name_match else game_name

            product_version_match = re.search(r'productVersion\s*:\s*["\']([^"\']+)["\']', r_desktop.text)
            product_version = product_version_match.group(1) if product_version_match else "1.0"
            
            # Format custom template
            formatted_html = HTML_TEMPLATE.format(
                game_title=game_name,
                loader_script=f"Build/{loader_filename}",
                company_name=company_name,
                product_name=product_name,
                product_version=product_version
            )
            
            # Write index.html
            index_path = os.path.join(game_dir, "index.html")
            with open(index_path, 'w', encoding='utf-8') as f:
                f.write(formatted_html)
                
            log_task(task_id, "Launcher index.html generated successfully.")
            
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
                
        else:
            log_task(task_id, "Not a standard Unity WebGL game or configuration not parsed. Falling back to default recursive crawler...")
            
            # 6. Fallback Crawl game assets
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
        elif path_str.startswith('/web/'):
            rel = path_str[5:]
            return os.path.join(WEB_DIR, rel)
        elif path_str.startswith('/api/'):
            return super().translate_path(path)
        else:
            rel = path_str.lstrip('/')
            if not rel:
                rel = 'index.html'
            return os.path.join(WEB_DIR, rel)
            
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept')
        self.end_headers()
            
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
