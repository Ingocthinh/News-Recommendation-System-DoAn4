# Hệ Thống Tin Tức & Gợi Ý Thông Minh (AI News Recommendation)

Dự án này là một nền tảng báo chí kỹ thuật số hoàn chỉnh, tích hợp Trí tuệ Nhân tạo (AI) để gợi ý nội dung báo chí cá nhân hóa theo thời gian thực (Real-time).

![Demo AI Recommendation](https://placehold.co/800x400/1e1e2a/6b6b85?text=Dự+Án+Tin+Tức+AI)

## Kiến Trúc Hệ Thống (Microservices)

Hệ thống được thiết kế theo chuẩn Enterprise, tách biệt hoàn toàn 4 luồng xử lý độc lập:
1. **Frontend (React/Vite):** Giao diện đọc báo mượt mà, hỗ trợ Dark Mode, thiết kế Responsive.
2. **Backend (Node.js/Express):** API Server kết nối Database (Prisma/SQLite), xử lý tải trang, log hành vi nhấp chuột (Click/Read) và xác thực người dùng.
3. **ML Service (Python/Flask):** "Bộ não" AI chuyên thực thi mô hình gợi ý lõi.
   - Sức mạnh thuật toán nằm ở kiến trúc **Hybrid** lai tạo giữa (1) Nhận diện nội dung TF-IDF văn bản, và (2) Lọc Cộng Tác Hành Vi Collaborative Filtering. Đạt độ chính xác (HitRate) cực kỳ ấn tượng lên tới **66%**.
4. **News Crawler (Python):** Robot tự động thu thập tin tức thời sự 24/7 từ VnExpress thông qua nền tảng cung cấp RSS chính quy, bóc tách và loại bỏ mã HTML rác.

---

## 🛠 Hướng Dẫn Cài Đặt và Khởi Chạy (Local)

Yêu cầu bắt buộc phải cài đặt trước trên máy tính:
- Python 3.10+
- Node.js 18+

### BƯỚC 1: Khởi động Dịch vụ Trí tuệ Nhân Tạo (ML)
Mở một Terminal mới, di chuyển vào folder `ml_service` và chạy:
```bash
cd ml_service
python -m venv .venv

# Trên Windows
.\.venv\Scripts\activate

# Cài thư viện lõi AI
pip install -r requirements.txt

# Gọi tự động train model và Mở API nội bộ Port 5000
python app.py
```

### BƯỚC 2: Khởi động Backend (API)
Mở một Terminal thứ 2, di chuyển vào `backend`:
```bash
cd backend
npm install
npx prisma generate
npx prisma db push

# Mở API Endpoint trên Port 3000
npm run dev
```

### BƯỚC 3: Khởi động Giao diện đọc báo (Frontend)
Mở một Terminal thứ 3, di chuyển vào `frontend`:
```bash
cd frontend
npm install

# Mở giao diện ứng dụng trên trình duyệt (thường là Port 5173 / localhost:5173)
npm run dev
```

---

## Đối tượng sử dụng
Dự án được dọn dẹp chuyên nghiệp (Clean Code), làm sản phẩm hoàn thiện sẵn sàng để làm Portfolio, Đồ án tốt nghiệp / kết thúc môn, hoặc nền tảng để phát triển startup nhỏ lĩnh vực tổng hợp và tái phân phối nội dung.
