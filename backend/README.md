# Portfolio AI Assistant Backend

Python FastAPI backend for the public professional portfolio. The website remains on GitHub Pages. The backend is deployed on Render. The GitHub Pages frontend stays in an unmerged pull request.

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
- The backend currently allows **8 requests per client IP / 15 minutes**, **60 provider attempts per rolling 24 hours per Python process**, and **2 simultaneous provider requests**. Excess requests return HTTP 429. These are conservative process-local safeguards, **not** a reliable account-wide quota: counters reset on restart and are not shared across instances. Monitor provider dashboards and add an edge/shared rate limiter before public launch.
- The knowledge file is intentionally public-only. Review each fact before deployment.
- Model output is not independently fact-verified. Evaluate unsupported claims and prompt injection before launch.
- The branch frontend points to the deployed Render backend, but protected public access is still disabled pending end-to-end verification.

Run tests: `pytest -q`.

## Public deployment security gate

The default is `PUBLIC_DEPLOYMENT=false`. In this mode the chat endpoint rejects non-local clients (it still works with localhost and the offline test client). This prevents an accidentally deployed public host from exposing the LLM without verification.

Before enabling public access:
1. Create a **free Cloudflare Turnstile** widget restricted to `taibfaiu-creator.github.io`.
2. Keep the **site key** in the future frontend widget and the **secret key** in backend hosting secrets only.
3. Set `PUBLIC_DEPLOYMENT=true`, `TURNSTILE_SECRET_KEY`, and `TURNSTILE_EXPECTED_HOSTNAME=taibfaiu-creator.github.io`.
4. On every chat request, the frontend must include a **fresh, single-use** `turnstile_token` from the widget. Backend verifies it using Cloudflare Siteverify before calling either LLM.
5. Add host-level request/body limits, a shared rate limiter, usage monitoring and budget controls. The current process-local caps (12 requests per IP/15min and 150 requests/day/process) reset on restart and do not form a guaranteed account-wide quota. CORS is not authorization.
6. Do not switch on public mode until the frontend widget and end-to-end tests are complete.

Turnstile reference: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
