# Content Maximizer

Engineering thesis project: AI software for B2B founder-led marketing.

Content Maximizer takes one long-form YouTube video or transcript and turns it into reusable content assets: clip ideas, blog sections, social posts, hooks, scripts, and strategy material. The core product idea is human-led creation with AI-assisted distribution: one strong long-form piece, then structured repurposing across platforms.

Demo video: https://www.youtube.com/watch?si=hqFjvQrk1d2l7Tdh&v=lDyF7flPJzM&feature=youtu.be

## What It Does

- Fetches YouTube transcripts or accepts uploaded transcript/context files.
- Uses Gemini to generate clips, blog/social assets, and business growth strategy outputs.
- Streams long-running AI jobs with NDJSON progress events.
- Saves projects, scripts, transcripts, and workflow artifacts locally as JSON.
- Supports async clip download/slicing jobs for local workflows.
- Includes documentation for architecture, API endpoints, persistence, security notes, and testing.

## Tech Stack

- Frontend: Vite, JavaScript, HTML, CSS
- Backend: Python, Flask, Flask-CORS
- AI: Gemini API, user-provided API key
- Media/transcripts: yt-dlp, ffmpeg, youtube-transcript-api
- Data: local JSON persistence with atomic writes
- Testing/docs: Playwright, backend tests, architecture notes

## Run Locally

Requirements:

- Python 3.10+
- Node.js 18+ and npm
- `ffmpeg` available in PATH
- Gemini API key from your own Google/Gemini account

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

Frontend:

```powershell
npm install
npm run dev
```

Open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:5000/api/health`

## Gemini API Key

No Gemini API key is included in this repository.

You can either:

1. Start the app and paste your key in the AI settings UI.
2. Or create `backend/.env` locally:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash
```

`backend/.env` is ignored by git.

## Example Data

Some example transcripts in this repository are AI-generated mock data used for testing and demonstration.

## Notes

This is a local prototype, not a production SaaS. The next production steps would be authentication, database-backed persistence, background workers, cloud deployment, better observability, and stricter multi-user data boundaries.
