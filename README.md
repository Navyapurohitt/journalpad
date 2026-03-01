<p align="center">
  <h1 align="center">journalpad</h1>
  <p align="center"><em>a quiet place to write</em></p>
</p>

<p align="center">
  <a href="https://journalpad.vercel.app">Live Demo</a> · 
  <a href="#features">Features</a> · 
  <a href="#tech-stack">Tech Stack</a> · 
  <a href="#architecture">Architecture</a> · 
  <a href="#getting-started">Getting Started</a>
</p>

---

**journalpad** is a distraction-free, ambient writing app built for people who just want to *write*. No accounts, no clutter — open the page, start typing, and share when you're ready.

I built this because every writing tool out there is either bloated with features or wants you to sign up before you can write a single word. journalpad strips all of that away and gives you a clean canvas with ambient soundscapes to help you focus.

## Features

- **Zero-friction writing** — no sign-up, no login. Open the page and start typing immediately
- **Ambient soundscapes** — 4 generative audio moods (Rain, Lo-fi, Deep Focus, Forest) synthesized in real-time using the Web Audio API — no external audio files, works fully offline
- **Keyboard typing sounds** — subtle mechanical key click feedback generated via audio synthesis for a tactile writing feel
- **Password-protected pads** — optionally lock your writing with a password before sharing. Passwords are hashed with bcrypt server-side; plaintext is never stored
- **Shareable links** — save your writing and get a unique short link. Anyone with the link can read it (or needs the password if protected)
- **Mood-reactive UI** — each ambient mood shifts the entire color palette, grain texture, and visual temperature of the interface via CSS custom properties
- **View counter** — see how many times your shared pad has been read
- **Auto-save drafts** — unsaved work persists in `localStorage` between sessions
- **Word count & read time** — live writing stats appear as you type
- **Responsive design** — works on desktop, tablet, and mobile

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Frontend** | Vanilla HTML/CSS/JS | Zero dependencies, instant load, no build step |
| **Typography** | Google Fonts (Quicksand, Geist Mono) | Clean, modern readability |
| **Audio Engine** | Web Audio API | Real-time procedural sound synthesis — no audio files to host or load |
| **Backend** | Python / FastAPI | Lightweight, async-capable, auto-generated API docs |
| **ORM** | SQLAlchemy 2.0 | Database-agnostic — same code for local SQLite and production PostgreSQL |
| **Auth** | passlib + bcrypt | Industry-standard password hashing with automatic salt |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Seamless local dev with zero config, robust production storage |
| **Hosting** | Vercel (frontend) + Railway (backend + DB) | Auto-deploy on every `git push` |

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   Frontend                        │
│            (Vercel — Static HTML)                  │
│                                                    │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Editor &   │  │  Web Audio   │  │  Mood     │ │
│  │  Pad Logic  │  │  Sound Engine│  │  Theming  │ │
│  └──────┬─────┘  └──────────────┘  └───────────┘ │
│         │ fetch()                                  │
└─────────┼──────────────────────────────────────────┘
          │ HTTPS
┌─────────▼──────────────────────────────────────────┐
│               Backend API (Railway)                 │
│              Python / FastAPI / Uvicorn              │
│                                                      │
│  POST /pads ─────────── Create pad (+ optional pwd) │
│  GET  /pads/:id/meta ── Check if protected           │
│  POST /pads/:id/read ── Fetch content (auth if pwd)  │
│  PUT  /pads/:id ─────── Update pad                   │
│  DELETE /pads/:id ───── Delete pad                   │
│  GET  /health ───────── Health check                 │
│                                                      │
│  ┌─────────────────┐    ┌────────────────────────┐  │
│  │  SQLAlchemy ORM  │───▶│  PostgreSQL (Railway)  │  │
│  └─────────────────┘    └────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

### How the Ambient Sound Engine Works

Instead of loading audio files from a CDN, journalpad generates all ambient sounds procedurally using the Web Audio API:

1. **White/Brown noise generation** — a buffer of random samples is created and looped. Brown noise applies a cumulative low-pass random walk for deeper, warmer sound
2. **Biquad filtering** — each mood applies a different filter type (`lowpass`, `bandpass`, `highpass`) with tuned frequency and Q values to shape the noise into rain, lo-fi static, brown noise, or wind
3. **Gain envelope** — smooth volume control with real-time slider adjustment via `AudioParam.setValueAtTime()`

This approach means **zero network requests** for audio, **zero hosted files**, and it works **completely offline**.

### How Password Protection Works

1. User saves a pad with a password → frontend sends plaintext to backend over HTTPS
2. Backend hashes the password with **bcrypt** (via passlib) with automatic salting → stores only the hash
3. Reader opens the shared link → backend returns metadata indicating the pad is protected (no content leaked)
4. Reader enters password → backend verifies against the stored hash → returns content only if matched
5. Plaintext passwords are **never stored** and **never logged**

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (for Vercel CLI only)
- Git

### Local Development

```bash
# Clone the repo
git clone https://github.com/Navyapurohitt/journalpad.git
cd journalpad

# Set up backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the API server
python3 -m uvicorn main:app --reload --port 8000
# → API running at http://localhost:8000
# → Interactive docs at http://localhost:8000/docs
```

In a separate terminal, open `frontend/index.html` in your browser. Update `API_BASE` in the script to `http://localhost:8000` for local development.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///./writingpad.db` (local SQLite) |

The backend automatically detects `postgres://` URLs from Railway and converts them to `postgresql://` for SQLAlchemy compatibility.

## Deployment

### Backend (Railway)

1. Push to GitHub
2. Create a new Railway project → Deploy from GitHub → set root directory to `backend`
3. Add a PostgreSQL plugin — Railway injects `DATABASE_URL` automatically
4. Generate a public domain under Settings → Networking

### Frontend (Vercel)

1. Update `API_BASE` in `frontend/index.html` to your Railway URL
2. Run `npx vercel --prod` from the `frontend/` directory
3. Update CORS origins in `backend/main.py` to your Vercel domain

## API Reference

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | None |
| `POST` | `/pads` | Create a new pad | None |
| `GET` | `/pads/:id/meta` | Get pad metadata (no content) | None |
| `POST` | `/pads/:id/read` | Read pad content | Password (if protected) |
| `PUT` | `/pads/:id` | Update pad content | Password (if protected) |
| `DELETE` | `/pads/:id` | Delete a pad | Password (if protected) |

Full interactive documentation available at `/docs` (Swagger UI) when running the backend.

## Project Structure

```
journalpad/
├── frontend/
│   └── index.html          # Complete SPA — editor, modals, sound engine, theming
├── backend/
│   ├── main.py             # FastAPI application — routes, models, auth
│   ├── requirements.txt    # Python dependencies
│   ├── Procfile             # Railway process config
│   └── railway.toml         # Railway build & deploy config
├── .gitignore
└── README.md
```

## Future Roadmap

- [ ] **Expiring pads** — auto-delete after 1 hour / 1 day / 1 week
- [ ] **Edit tokens** — secret link to update a pad after sharing
- [ ] **Markdown preview** — toggle between raw text and rendered markdown
- [ ] **Custom slugs** — choose your own URL like `journalpad.vercel.app/?id=my-thoughts`
- [ ] **Export** — download as `.txt` or `.md`
- [ ] **Focus/typewriter mode** — dim all lines except the current one

## License

MIT — do whatever you want with it.

---

<p align="center"><em>built by <a href="https://github.com/Navyapurohitt">navya</a></em></p>
