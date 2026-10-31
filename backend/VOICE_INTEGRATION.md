# ElevenLabs Voice integration (review branch)

This adds an optional voice button to the existing portfolio assistant without replacing Gemini/Groq text chat.

## Required configuration

1. In ElevenLabs, change VoiceAgent Lab's system prompt and knowledge base to answer **only** questions about Al-Tayeb Talal's publicly verifiable professional profile. Do not use bank-internal data or secrets.
2. Publish the agent configuration in ElevenLabs (publishing the agent configuration is distinct from making it publicly accessible). Turn on **authentication required** for the agent. Do not enable the domain allowlist simultaneously with signed-URL authentication.
3. On Render > altayeb-ai-backend > Environment, add:
   - `ELEVENLABS_API_KEY` = a scoped, secret key
   - `ELEVENLABS_AGENT_ID` = agent ID from ElevenLabs (not the branch ID)
   - Preserve `PUBLIC_DEPLOYMENT=true`, `TURNSTILE_SECRET_KEY`, `TURNSTILE_EXPECTED_HOSTNAME` and `ALLOWED_ORIGINS`.
4. Redeploy Render from the intended branch for a staging test. Main deployment must remain untouched until review.
5. Serve the site's feature-branch `index.html` locally over HTTP and backend locally with valid test env. Confirm Turnstile verification, permission prompt, Arabic and English audio, disconnect, and existing text chat.
6. Only after successful tests, review and merge this PR, then redeploy Render as appropriate.

## Security/cost notes

The endpoint `POST /api/voice/signed-url` validates Cloudflare Turnstile, reuses the **in-memory** rate limit, and only returns the short-lived signed WebSocket URL. No ElevenLabs API key is sent to the browser. A signed URL **is a bearer credential**: avoid logging or sharing it.

**Important:** In-memory rate limiting is not a guaranteed spending cap. Reboots/multiple workers reset or partition counters, and the issued signed URL can be used to run a potentially lengthy conversation. Before broad public release, implement a real budget cap / platform spending limit, monitor ElevenLabs usage, and consider server-side session limits.

The frontend loads the ElevenLabs JavaScript SDK through an ESM CDN on first use. For production hardening, pin an audited SDK version and self-host/bundle it (for example via npm). Verify compatibility with Content Security Policy before release.

## Expected API responses

`POST /api/voice/signed-url`
Request: `{"turnstile_token":"<fresh token>"}`
Successful response: `{"signed_url":"wss://api.elevenlabs.io/..."}`
503: ElevenLabs environment variables missing.
403: Turnstile authorization failed.
429: existing per-IP limiter.
502: ElevenLabs connection or upstream issue.

References:
- https://elevenlabs.io/docs/eleven-agents/customization/authentication
- https://elevenlabs.io/docs/eleven-agents/libraries/java-script
- https://elevenlabs.io/docs/eleven-agents/api-reference/conversations/get-signed-url
