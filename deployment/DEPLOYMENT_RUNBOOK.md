# Verity — Deployment Runbook

**Provider:** Vercel (Hobby, free) · **Stack:** Python 3.12 stdlib, no build step
· **Version:** 0.1.0 · **Date:** 12 Nov 2026

## 1. What gets deployed

- `api/index.py` — WSGI adapter; Vercel turns it into a serverless function.
- `app/` — `service.py` (single request handler), `search.py`, `synthesize.py`,
  `index.html` (single-page UI). `app/server.py` is local-dev only.
- `vercel.json` — rewrites every path to `/api/index`.
- No database, no sessions, no writes. Every answer is computed live from
  the search providers.

## 2. Deploy steps (main agent)

1. Create the public GitHub repo `MSAbhishek22/verity` and push this folder
   (see `README.md` submission checklist).
2. Vercel → Add New Project → Import the repo. Framework preset: **Other**.
   No build command. No output directory. Root directory: repo root.
3. Environment variables (optional): `TAVILY_API_KEY` — only if the user
   supplies a Tavily key (every Geek Room participant gets 8,000 credits).
   Without it the app uses Wikipedia and says so on screen. **Never commit
   a key; set it in the Vercel dashboard only.**
4. Deploy. Note the deployment URL (e.g. `https://verity-*.vercel.app`).

## 3. Health checks (run against the production URL)

```bash
curl -s https://<deploy-url>/api/health
# {"ok": true, "service": "verity", "version": "0.1.0", "provider": "wikipedia"}

curl -s https://<deploy-url>/api/status
# {"service": "verity", "version": "0.1.0", "provider": "wikipedia",
#  "tavily_configured": false, "fallback": "wikipedia", ...}

curl -s -X POST https://<deploy-url>/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "How does photosynthesis work?"}'
# expect 200, verdict GROUNDED or PARTIAL, claims[] with source URLs
```

Then open the URL in a fresh browser session, ask a question, and confirm:
the verdict renders, citation chips jump to source cards, the constellation
rotates, and the browser console shows 0 errors.

## 4. Known platform constraint

Vercel Hobby serverless functions time out at ~10 s. Verity's search budget
is 9 s (`OVERALL_BUDGET` in `app/search.py`: both providers in parallel,
8 s per call). If a provider is slow, the function can time out before the
answer returns — the UI then shows a network error with retry. This is
acceptable for a prototype; do **not** raise the budget above the platform
timeout.

## 5. Rollback

Redeploy the previous commit from the Vercel dashboard (Deployments →
previous deployment → Promote to Production), or `git revert` and push —
Vercel auto-deploys from the production branch.

## 6. Ownership

- Builder: M S Abhishek (MSAbhishek22) — Geek Room team `ms2539`.
- Code: this repo. Secrets: none in code; `TAVILY_API_KEY` only via env var.
