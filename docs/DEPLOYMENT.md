# 🚀 Hướng Dẫn Deploy - Traffic Law QA System

Hướng dẫn chi tiết để deploy hệ thống chatbot hỏi đáp luật giao thông Việt Nam.

## 📑 Mục Lục

- [Tổng Quan Kiến Trúc](#tổng-quan-kiến-trúc)
- [Yêu Cầu Hệ Thống](#yêu-cầu-hệ-thống)
- [1. Chuẩn Bị Qdrant Cloud](#1-chuẩn-bị-qdrant-cloud)
- [2. Deploy Backend](#2-deploy-backend)
  - [2.1 Chạy với Docker](#21-chạy-với-docker)
  - [2.2 Deploy lên Railway](#22-deploy-lên-railway)
  - [2.3 Deploy lên Render](#23-deploy-lên-render)
  - [2.4 Deploy lên VPS](#24-deploy-lên-vps)
- [3. Deploy Frontend lên Vercel](#3-deploy-frontend-lên-vercel)
- [4. CI/CD với GitHub Actions](#4-cicd-với-github-actions)
- [5. Kiểm Tra Sau Deploy](#5-kiểm-tra-sau-deploy)
- [6. Troubleshooting](#6-troubleshooting)

---

## Tổng Quan Kiến Trúc

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Frontend       │────▶│  Backend        │────▶│  Qdrant Cloud   │
│  (Vercel)       │     │  (Railway/VPS)  │     │  (Vector DB)    │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │                 │
                        │  OpenAI API     │
                        │                 │
                        └─────────────────┘
```

---

## Yêu Cầu Hệ Thống

### Đã chuẩn bị sẵn:
- ✅ Tài khoản [Qdrant Cloud](https://cloud.qdrant.io/) (free tier đủ dùng)
- ✅ OpenAI API Key
- ✅ GitHub repository đã push code

### Cần đăng ký:
- 📝 Tài khoản [Vercel](https://vercel.com/) (cho Frontend)
- 📝 Tài khoản [Railway](https://railway.app/) hoặc [Render](https://render.com/) (cho Backend)

---

## 1. Chuẩn Bị Qdrant Cloud

### Bước 1: Tạo Cluster

1. Đăng nhập [Qdrant Cloud Console](https://cloud.qdrant.io/)
2. Click **"Create Cluster"**
3. Chọn **Free Tier** (1GB storage, đủ cho demo)
4. Chọn region gần Việt Nam nhất (Singapore hoặc Tokyo)
5. Click **"Create"**

### Bước 2: Lấy Thông Tin Kết Nối

Sau khi cluster được tạo, lấy:
- **Cluster URL**: `https://xxx-xxx.aws.cloud.qdrant.io:6333`
- **API Key**: Click "API Keys" → "Create API Key"

### Bước 3: Upload Data vào Qdrant Cloud

```bash
# Cập nhật .env với Qdrant Cloud credentials
QDRANT_URL=https://xxx-xxx.aws.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# Chạy script upload data
cd vectorDB
python main.py
```

> **Lưu ý**: Chỉ cần chạy 1 lần để upload data ban đầu.

---

## 2. Deploy Backend

### 2.1 Chạy với Docker

#### Build Image

```bash
# Build image
docker build -t traffic-law-backend:v1 .
```

#### Chạy Container

```bash
# Tạo file .env (copy từ .env.example và điền thông tin)
cp .env.example .env

# Chạy với docker-compose
docker compose up -d

# Xem logs
docker compose logs -f backend

# Dừng services
docker compose down
```

#### Chạy thủ công (không dùng docker-compose)

```bash
docker run -d \
  --name traffic-law-backend \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-openai-key \
  -e QDRANT_URL=https://xxx.cloud.qdrant.io:6333 \
  -e QDRANT_API_KEY=your-qdrant-key \
  -e SERVER_API_KEY=your-server-api-key \
  traffic-law-backend
```

---

### 2.2 Deploy lên Railway

Railway là platform đơn giản, hỗ trợ Docker và auto-deploy từ GitHub.

#### Bước 1: Kết nối GitHub

1. Đăng nhập [Railway](https://railway.app/)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Chọn repository `traffic-law-qa-system`

#### Bước 2: Cấu hình Service

1. Railway sẽ tự detect `Dockerfile`
2. Vào **Settings** → **Variables**, thêm các biến:

```env
OPENAI_API_KEY=sk-xxx
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=xxx
SERVER_API_KEY=your-secret-key
BACKEND_PORT=8000
```

#### Bước 3: Generate Domain

1. Vào **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Copy URL (ví dụ: `https://traffic-law-backend-xxx.up.railway.app`)

#### Bước 4: Kiểm tra

```bash
curl https://your-railway-url.up.railway.app/health
```

---

### 2.3 Deploy lên Render

Render cũng là lựa chọn tốt với free tier.

#### Bước 1: Tạo Web Service

1. Đăng nhập [Render Dashboard](https://dashboard.render.com/)
2. Click **"New"** → **"Web Service"**
3. Kết nối GitHub repo

#### Bước 2: Cấu hình

- **Name**: `traffic-law-backend`
- **Runtime**: `Docker`
- **Branch**: `main`
- **Instance Type**: Free (hoặc Starter $7/tháng)

#### Bước 3: Environment Variables

Thêm các biến môi trường:

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | `sk-xxx` |
| `QDRANT_URL` | `https://xxx.cloud.qdrant.io:6333` |
| `QDRANT_API_KEY` | `xxx` |
| `SERVER_API_KEY` | `your-secret-key` |
| `BACKEND_PORT` | `8000` |

#### Bước 4: Deploy

Click **"Create Web Service"** và đợi deploy hoàn tất.

---

### 2.4 Deploy lên VPS

Nếu bạn có VPS (Ubuntu 22.04+):

#### Bước 1: Cài đặt Docker

```bash
# SSH vào VPS
ssh user@your-vps-ip

# Cài Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Cài Docker Compose
sudo apt install docker-compose-plugin -y

# Thêm user vào group docker
sudo usermod -aG docker $USER
newgrp docker
```

#### Bước 2: Clone và Deploy

```bash
# Clone repository
git clone https://github.com/LeNguyenAnhKhoa/traffic-law-qa-system.git
cd traffic-law-qa-system

# Tạo file .env
cp .env.example .env
nano .env  # Điền thông tin

# Deploy
docker compose up -d

# Kiểm tra
docker compose ps
docker compose logs -f
```

#### Bước 3: Setup Nginx Reverse Proxy (Tùy chọn)

```bash
# Cài Nginx
sudo apt install nginx -y

# Tạo config
sudo nano /etc/nginx/sites-available/traffic-law-api
```

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/traffic-law-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Cài SSL với Certbot
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.yourdomain.com
```

---

## 3. Deploy Frontend lên Vercel

### Bước 1: Import Project

1. Đăng nhập [Vercel](https://vercel.com/)
2. Click **"Add New..."** → **"Project"**
3. Import repository từ GitHub
4. Chọn **Root Directory**: `frontend`

### Bước 2: Cấu hình Build

Vercel sẽ tự detect Next.js. Kiểm tra settings:

- **Framework Preset**: Next.js
- **Build Command**: `pnpm build` (hoặc `npm run build`)
- **Output Directory**: `.next`
- **Install Command**: `pnpm install` (hoặc `npm install`)

### Bước 3: Environment Variables

Thêm các biến môi trường:

| Name | Value |
|------|-------|
| `NEXT_PUBLIC_BACKEND_URL` | `https://your-backend-url.railway.app` (URL backend đã deploy) |
| `NEXT_PUBLIC_BACKEND_API_KEY` | `your-server-api-key` |

> ⚠️ **Quan trọng**: `NEXT_PUBLIC_BACKEND_URL` phải là URL của backend đã deploy (Railway/Render/VPS), không phải `localhost`!

### Bước 4: Deploy

Click **"Deploy"** và đợi khoảng 1-2 phút.

### Bước 5: Custom Domain (Tùy chọn)

1. Vào **Settings** → **Domains**
2. Thêm domain của bạn
3. Cập nhật DNS records theo hướng dẫn của Vercel

### Vercel CLI (Alternative)

```bash
# Cài Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy từ thư mục frontend
cd frontend
vercel

# Deploy production
vercel --prod
```

---

## 4. CI/CD với GitHub Actions

Repository đã được cấu hình sẵn 2 workflows:

### Backend CI/CD (`.github/workflows/backend-ci.yml`)

**Triggers:**
- Push/PR vào `main` hoặc `develop` branch
- Thay đổi trong `backend/`, `Dockerfile`, `docker-compose.yaml`

**Jobs:**
1. **Lint & Test**: Kiểm tra code style với flake8, black, isort
2. **Build**: Build Docker image
3. **Push**: Push image lên GitHub Container Registry (chỉ khi push vào `main`)
4. **Deploy**: Deploy lên production (cần cấu hình thêm)

### Frontend CI (`.github/workflows/frontend-ci.yml`)

**Triggers:**
- Push/PR vào `main` hoặc `develop` branch
- Thay đổi trong `frontend/`

**Jobs:**
1. **Lint & Build**: Kiểm tra TypeScript và build Next.js

### Cấu hình Secrets

Vào **Repository Settings** → **Secrets and variables** → **Actions**, thêm:

| Secret Name | Description |
|-------------|-------------|
| `NEXT_PUBLIC_BACKEND_API_KEY` | API key cho frontend |

### Cấu hình Variables

Vào **Repository Settings** → **Secrets and variables** → **Actions** → **Variables**, thêm:

| Variable Name | Value |
|---------------|-------|
| `NEXT_PUBLIC_BACKEND_URL` | URL backend production |

### Auto Deploy Backend (Tùy chọn)

Để tự động deploy backend khi push code, bạn có thể:

#### Option 1: Railway Auto Deploy
Railway tự động redeploy khi có push vào branch đã kết nối.

#### Option 2: Render Auto Deploy
Render cũng hỗ trợ auto deploy từ GitHub.

#### Option 3: VPS với SSH
Uncomment phần deploy trong workflow và thêm secrets:

```yaml
- name: Deploy to VPS
  uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.VPS_HOST }}
    username: ${{ secrets.VPS_USERNAME }}
    key: ${{ secrets.VPS_SSH_KEY }}
    script: |
      cd /path/to/traffic-law-qa-system
      git pull
      docker compose pull
      docker compose up -d
```

Thêm secrets:
- `VPS_HOST`: IP của VPS
- `VPS_USERNAME`: username SSH
- `VPS_SSH_KEY`: Private key SSH

---

## 5. Kiểm Tra Sau Deploy

### Backend Health Check

```bash
# Kiểm tra health endpoint
curl https://your-backend-url/health

# Expected response:
# {"status": "healthy"}
```

### Test API

```bash
# Test chat endpoint
curl -X POST https://your-backend-url/api/v0/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-server-api-key" \
  -d '{
    "query": "Mức phạt vượt đèn đỏ là bao nhiêu?",
    "chat_history": [],
    "user_id": "test-user"
  }'
```

### Frontend

1. Mở URL Vercel trong browser
2. Gửi tin nhắn test
3. Kiểm tra Console browser xem có lỗi CORS không

---

## 6. Troubleshooting

### Lỗi CORS

Nếu frontend không gọi được backend, kiểm tra:

1. Backend đã cấu hình CORS cho domain frontend:
```python
# backend/app.py đã có sẵn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc specific domain
    ...
)
```

2. URL backend trong frontend không có trailing slash:
```env
# ✅ Đúng
NEXT_PUBLIC_BACKEND_URL=https://api.example.com

# ❌ Sai
NEXT_PUBLIC_BACKEND_URL=https://api.example.com/
```

### Backend không start được

```bash
# Xem logs
docker compose logs backend

# Các lỗi phổ biến:
# 1. Thiếu env vars → Kiểm tra .env file
# 2. Qdrant connection failed → Kiểm tra QDRANT_URL và QDRANT_API_KEY
# 3. Port conflict → Đổi BACKEND_PORT
```

### Docker build chậm

```bash
# Sử dụng BuildKit để build nhanh hơn
DOCKER_BUILDKIT=1 docker build -t traffic-law-backend .

# Hoặc set trong docker-compose.yaml
# Đã được optimize với multi-stage build
```

### Vercel build failed

1. Kiểm tra Node.js version trong `package.json`:
```json
{
  "engines": {
    "node": ">=18"
  }
}
```

2. Kiểm tra pnpm-lock.yaml có match với package.json

3. Thêm `.nvmrc` file:
```
22
```

### Rate Limit OpenAI

Nếu gặp lỗi rate limit:
1. Upgrade OpenAI plan
2. Implement caching/queue
3. Giảm `HYBRID_SEARCH_TOP_K` và `RERANK_TOP_K`

---

## 📚 Tài Liệu Tham Khảo

- [Qdrant Cloud Documentation](https://qdrant.tech/documentation/cloud/)
- [Vercel Documentation](https://vercel.com/docs)
- [Railway Documentation](https://docs.railway.app/)
- [Docker Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## 💡 Tips

1. **Development vs Production**:
   - Dev: Chạy local với `docker compose up`
   - Prod: Deploy backend lên Railway/Render, frontend lên Vercel

2. **Cost Optimization**:
   - Qdrant Cloud Free: 1GB (đủ cho ~100k vectors)
   - Railway Free: $5 credit/tháng
   - Vercel Free: Unlimited cho personal projects
   - Render Free: 750 hours/tháng (auto sleep sau 15 phút không hoạt động)

3. **Security**:
   - Không commit `.env` file
   - Sử dụng secrets trong CI/CD
   - Enable HTTPS cho tất cả endpoints
   - Rotate API keys định kỳ

---

**Happy Deploying! 🚀**
