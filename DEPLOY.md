# Deployment notes (nothing here has been deployed or tested online)

**Why not all-on-Vercel:** InsightFace + onnxruntime + the ~330 MB `buffalo_l` model pack exceed Vercel serverless size/runtime limits,
and SQLite needs a persistent disk. So: **one Docker service runs everything** (UI + API + AI + SQLite).
Vercel is optional and only acts as a front door that proxies to that service.

## 1. Backend (the real app) — any Docker host with a persistent disk
Render / Fly.io / Railway / a VPS / Hugging Face Spaces (Docker). Needs ≥ 2 GB RAM recommended; CPU is enough.

`demo_assets/` is private and git-ignored, so it is **not** in a normal GitHub clone. Choose one:
* **A (recommended):** build the image on your machine where `demo_assets/` exists, push to a **private** registry, deploy that image.
  ```bash
  docker build -t smart-attendance-demo .
  docker run -p 8000:8000 -v sa_data:/data -e SECRET_KEY=$(openssl rand -hex 32) smart-attendance-demo
  ```
* **B:** a **private** repo that also contains `demo_assets/` (remove it from `.gitignore` in that private repo only).

Set env: `SECRET_KEY`, `DATA_DIR=/data` (mounted persistent volume), `ASSET_DIR=/srv/demo_assets`. Health check: `/health`.
First boot seeds the DB and enrols the 18 face profiles; data then persists on the volume. Use 1 gunicorn worker (model loaded once).
Free tiers that sleep or have ephemeral disks will lose uploads/PDFs/finalized sessions — use a persistent volume.

## 2. Optional Vercel front door (one public frontend URL)
Edit `vercel.json`, replace `YOUR-BACKEND-HOST`, then `vercel --prod`. Vercel rewrites proxy every path to the backend.
**Untested:** Vercel may cap request body size on proxied uploads. If the 4-photo upload fails through Vercel,
use the backend URL directly for the presentation (it is a complete working site on its own).

## 3. Acceptance check after deploying (do it yourself)
Open URL → admin login → 128 students → subjects/groups/assignments → logout → teacher login → only own classes →
start Data Science → upload the 4 images → AI → review → finalize → both PDFs on your phone → reload and confirm data persists.
