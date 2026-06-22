# 🕹️ ArcadeBox - CrazyGames Offline Downloader & Player

**ArcadeBox** là một công cụ giúp bạn tải các game từ trang web **CrazyGames** về máy tính cá nhân để có thể chơi offline mọi lúc, mọi nơi, không lo quảng cáo và không cần kết nối mạng.

Công cụ hỗ trợ tải game **HTML5**, **WebGL (Unity, Phaser, Construct, v.v.)** và tự động thêm các HTTP headers nén (.br / .gzip) thích hợp để game chạy mượt mà ngay trên máy của bạn.

---

## ✨ Tính năng chính (Key Features)
*   **Tải tự động chỉ với 1 click:** Chỉ cần dán link game CrazyGames (ví dụ: `https://www.crazygames.com/game/ragdoll-archers`) và ấn nút Download.
*   **Tải tài nguyên đệ quy (Recursive Crawler):** Tự động phát hiện và tải xuống tất cả tài nguyên liên quan (JS, CSS, WASM, `.data.br`, hình ảnh, âm thanh, v.v.) của game.
*   **Giao diện Dashboard Gaming Premium:** Giao diện tối hiện đại, hiệu ứng neon rực rỡ, hiển thị danh sách game trực quan.
*   **Trình chơi game tích hợp (Built-in Web Player):** Chơi game ngay trên Dashboard qua cửa sổ popup tiện lợi có hỗ trợ nút **Chơi Toàn Màn Hình (Fullscreen)**.
*   **Console Logging Real-time:** Xem tiến trình cào và tải file trong cửa sổ dòng lệnh (Console) mô phỏng kiểu terminal lập trình viên.
*   **Offline Web Server (Custom Headers):** Hỗ trợ trả về header `Content-Encoding: br` và `Content-Encoding: gzip` tự động, giúp khắc phục lỗi nén WASM của game Unity WebGL khi chạy ở local.

---

## 🛠️ Hướng dẫn cài đặt & Chạy (How to Run)

### 1. Chuẩn bị (Prerequisites)
Bạn cần máy tính đã cài đặt sẵn **Python 3** và thư viện `requests`:
```bash
pip install requests
```

### 2. Khởi chạy Server (Start Server)
Mở cửa sổ dòng lệnh (Terminal/PowerShell) tại thư mục dự án và chạy file `server.py`:
```bash
python server.py
```
Sau khi chạy, bạn sẽ thấy thông báo:
```text
==================================================
🕹️  ArcadeBox server started successfully!
👉 Open in browser: http://localhost:8000
==================================================
```

### 3. Tận hưởng (Usage)
1.  Truy cập địa chỉ `http://localhost:8000` trên trình duyệt web của bạn.
2.  Lấy một link game từ CrazyGames (ví dụ: `https://www.crazygames.com/game/basket-random`).
3.  Dán link vào ô nhập liệu ở phần **Download New Game** và chọn **Download**.
4.  Theo dõi tiến trình tải ở bảng điều khiển console. Khi hoàn tất, game sẽ xuất hiện trong phần **My Arcade Library**.
5.  Ấn nút **Play Offline** để mở cửa sổ chơi game trực tiếp!

---

## 📁 Cấu trúc thư mục (Project Structure)
*   `server.py`: File code backend Python, xử lý Web Server, APIs, Custom Compression Headers và luồng tải game chạy ngầm.
*   `web/`: Thư mục chứa giao diện web Dashboard (HTML, CSS, JS).
*   `games/`: Thư mục lưu trữ các game sau khi được tải về (tự động phân loại theo slug game).
*   `games_metadata.json`: Lưu trữ thông tin chi tiết các game đã tải để hiển thị lên thư viện.
