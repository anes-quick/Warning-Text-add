# Warning Text Tool - Deploy Guide

This project has:
- Frontend: `tool-template/index.html` (deploy to Vercel)
- Backend: `tool-template/backend` via `tool-template/Dockerfile` (deploy to Railway)

## 1) Push code to GitHub

From repository root:

```bash
git add .
git commit -m "Build warning text tool with before/after UI and ffmpeg processing"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

If remote already exists, use:

```bash
git push
```

## 2) Deploy backend on Railway

1. Create a new Railway project from GitHub.
2. Select this repo.
3. Set **Root Directory** to `tool-template`.
4. Railway should build with `tool-template/Dockerfile`.
5. Deploy and copy the public backend URL.

Health check:

`https://<your-railway-url>/api/health` should return `{"status":"ok"}`.

## 3) Deploy frontend on Vercel

1. Create a new Vercel project from the same GitHub repo.
2. Set **Root Directory** to `tool-template`.
3. Deploy.

## 4) Point frontend to backend

Edit `tool-template/index.html` in `resolveApiBase()` and replace:

```js
return 'https://YOUR-RAILWAY-APP.up.railway.app';
```

with your real Railway backend URL, then:

```bash
git add tool-template/index.html
git commit -m "Point frontend to Railway backend URL"
git push
```

Vercel redeploys automatically.

## 5) Final smoke test

1. Open Vercel URL
2. Upload a video
3. Select `Bottom.png` or `Top.png`
4. Click **Process video**
5. Confirm:
   - before/after previews load
   - output downloads with original filename + ` (1).mp4`

## Optional: Restrict access to only you

Use Cloudflare Access (email login) in front of the Vercel URL.
This is usually better than IP filtering.
