# Portfolio AI Assistant Backend

Python FastAPI backend for the public professional portfolio. The website remains on GitHub Pages. This backend is **not deployed** yet.

## Providers and free-tier policy

- Primary: Gemini API, using the model named by `GEMINI_MODEL`.
- Fallback: Groq API, using the model named by `GROQ_MODEL`.
- If both fail, an explicitly labeled static profile summary is returned.
- There is **no automatic paid upgrade**. Monitor each provider's actual free-tier usage and quotas.

## Local setup

```bash
cd backend
python -m venv .venv
# Activate the virtual environment for your OS
pip install -r requirements.txt
```

Copy `.env.example` to `.env` within `backend/` and fill it locally, or configure these values in your operating system or hosting service. The app reads `.env` automatically. **Never commit keys.**

```text
GEMINI_API_KEY=<secret>
GEMINI_MODEL=<free-tier-model-name-available-to-your-account>
GROQ_API_KEY=<secret>
GROQ_MODEL=<free-tier-model-name-available-to-your-account>
ALLOWED_ORIGINS=https://taibfaiu-creator.github.io
```

Start locally:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Health check: `GET /health`. Chat: `POST /api/chat` with JSON `{"message":"What are Al-Tayeb's skills?","history":[]}`.

## Deployment notes

- Deploy only after reviewing quota limits and configuring the four provider variables as *secrets* on the host.
- Do not expose the keys or host the Python backend directly on GitHub Pages.
- Configure HTTPS, trusted proxy headers, bounded request sizes, public-facing abuse protection, and deployment-level budget limits.
- Current in-process rate limits are a minimal local safety net, **not** a sufficient distributed/global rate limit for production. Add an edge rate limiter before going public.
- The knowledge file is intentionally public-only. Review each fact before deployment.
- Model output is not independently fact-verified. Evaluate unsupported claims and prompt injection before launch.
- No browser frontend has been connected yet.

Run tests: `pytest -q`.
