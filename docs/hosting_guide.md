# 🚀 Al-Aqabawi Dental Clinic - Deployment & Hosting Guide

This guide provides comprehensive, step-by-step instructions for testing and deploying the **Al-Aqabawi Dental Clinic AI Chatbot & CRM System** (FastAPI Backend + React Frontend).

---

## 📌 Overview of Hosting Strategies

| Strategy | Ideal Use Case | Backend | Frontend | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Instant Mobile Access** | Local testing & mobile live demo | Local FastAPI (`uv`) | Local React (`vite`) + `localtunnel` | **Free** |
| **Vercel Monorepo** | Full-stack serverless hosting | Vercel Serverless (`@vercel/python`) | Vercel Edge CDN (`@vercel/static-build`) | **Free Tier** |
| **Decoupled Architecture** | High-traffic / persistent backend | Railway / Render | Vercel / Netlify | **Free Tier** |

---

## 1. 📱 Instant Mobile Access & Local Tunneling (Development & Testing)

Use this method to test the chatbot on a physical smartphone or share a live demo with team members instantly from your development machine.

### Prerequisites
- Node.js & `npm`
- Python package manager `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- `npx` (comes with Node.js)

### Launch Command
Run the automated tunnel script from the project root:

```bash
./tunnel_spin_up.sh
```

### How It Works
1. Starts the FastAPI backend using `uv` on `http://localhost:8000`.
2. Starts the React frontend dashboard on `http://localhost:5173`.
3. Launches `npx localtunnel --port 5173` to generate a public HTTPS URL (e.g., `https://curly-lemons-trade.loca.lt`).

### Mobile Access & Localtunnel Verification
1. Open the printed `https://<subdomain>.loca.lt` URL on your mobile browser.
2. If Localtunnel presents a **Friendly Reminder / Tunnel Password** splash page:
   - Click the button or enter your local IP address.
   - You can quickly copy your public IP using:
     ```bash
     curl https://loca.lt/mytunnelpassword
     ```
3. Submit the IP on the splash page to unlock the live React mobile application.

### Alternative Tunneling Tools
If `localtunnel` is slow or unavailable, you can use these alternative tools:
- **Cloudflare Tunnel (Recommended alternative)**:
  ```bash
  npx cloudflared tunnel --url http://localhost:5173
  ```
- **Ngrok**:
  ```bash
  ngrok http 5173
  ```

---

## 2. ⚡ Free Permanent Hosting: Option A — Vercel Monorepo Deployment

Deploy both the FastAPI backend and React frontend together on **Vercel** using the included `vercel.json`.

### Architecture Breakdown (`vercel.json`)
The project includes a root `vercel.json` configured for Vercel's multi-builder environment:
- `@vercel/python` builds `backend/api/index.py` for API routes (`/api/*`, `/docs`, `/openapi.json`).
- `@vercel/static-build` compiles `frontend/package.json` into static assets (`frontend/dist`).

```json
{
  "version": 2,
  "builds": [
    {
      "src": "backend/api/index.py",
      "use": "@vercel/python"
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "dist"
      }
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "backend/api/index.py"
    },
    {
      "src": "/docs",
      "dest": "backend/api/index.py"
    },
    {
      "src": "/openapi.json",
      "dest": "backend/api/index.py"
    },
    {
      "handle": "filesystem"
    },
    {
      "src": "/(.*)",
      "dest": "frontend/index.html"
    }
  ]
}
```

### Steps to Deploy on Vercel

#### 1. Deploying via Vercel CLI (Fastest)
```bash
# Install Vercel CLI globally (if not already installed)
npm install -g vercel

# Login to Vercel
vercel login

# Deploy production build from root directory
vercel --prod
```

#### 2. Deploying via Vercel Web Dashboard (Git Integration)
1. Push your repository to GitHub / GitLab / Bitbucket.
2. Go to [Vercel New Project](https://vercel.com/new).
3. Import `dental-clinic-bot`.
4. Select **Root Directory** as `./`.
5. Add Environment Variables:
   - `OPENAI_API_KEY`: Your OpenAI API key for the AI bot engine.
   - `ENV`: `production`
6. Click **Deploy**. Vercel will automatically detect `vercel.json` and build both frontend and backend.

---

## 3. 🌐 Free Permanent Hosting: Option B — Decoupled Architecture (Railway / Render + Vercel)

For persistent backend processes, database storage, or heavy loads, host the Python backend on **Railway** or **Render** and the React frontend on **Vercel**.

---

### Part 1: Deploy Backend on Railway or Render

#### A. Deployment on Railway (Recommended for Python)
1. Log in to [Railway.app](https://railway.app/).
2. Click **New Project** -> **Deploy from GitHub repo**.
3. Select `dental-clinic-bot` and set the Root Directory to `backend`.
4. Set Build & Start Commands:
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Set Environment Variables:
   - `OPENAI_API_KEY`: `<your_openai_api_key>`
6. Railway will assign a public domain (e.g., `https://al-aqabawi-backend.up.railway.app`).

#### B. Deployment on Render
1. Log in to [Render.com](https://render.com/).
2. Create a **New Web Service** connected to your repository.
3. Settings:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - `OPENAI_API_KEY`: `<your_openai_api_key>`

---

### Part 2: Deploy Frontend on Vercel

1. Import project into Vercel setting **Root Directory** to `frontend`.
2. Framework Preset: **Vite**.
3. Build Settings:
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Environment Variables:
   - Set `VITE_API_BASE_URL` to your backend URL (e.g., `https://al-aqabawi-backend.up.railway.app`).

---

### Part 3: CORS Setup in Backend

In `backend/app.py`, update `CORSMiddleware` to authorize requests from your custom Vercel domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://al-aqabawi-clinic.vercel.app",  # Your production frontend domain
        "*"  # Or keep wildcard during testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 4. 🗄️ Database & State Management in Production

- **Local SQLite (`clinic.db`)**: Suitable for single-container deployments with persistent volumes (such as Railway persistent disks).
- **Stateless Serverless (Vercel Serverless Functions)**: Serverless functions reset state between cold starts. For permanent production booking records across serverless instances, connect to **Cloud Supabase (PostgreSQL)** or **Railway Postgres**.

---

## 5. ✅ Post-Deployment Verification Checklist

1. **Frontend UI**: Open your deployed Vercel URL and check that clinic services, doctor slots, and booking modals render cleanly.
2. **Swagger Docs**: Visit `<YOUR_BACKEND_URL>/docs` (or `<VERCEL_URL>/docs`) to verify interactive OpenAPI documentation.
3. **Chatbot Flow**: Send a message in the chat widget (e.g., *"أريد حجز موعد مع الدكتور أحمد"*) and verify the AI response and slot recommendations.
4. **Mobile Verification**: Test on mobile browsers (iOS Safari / Android Chrome) to verify responsiveness and tap interactions.
