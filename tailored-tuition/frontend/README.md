# Tailored Tuition — frontend

Next.js 16 (App Router) + Tailwind CSS 4. Maths is rendered with KaTeX via
react-markdown + remark-math + rehype-katex. The browser only calls same-origin
`/api/...`; Next rewrites those to the FastAPI backend.

```bash
npm install
npm run dev          # http://localhost:3000, expects the backend on :8000
npm run lint && npm run typecheck && npm run build
```

`BACKEND_URL` (default `http://localhost:8000`) is read by `next.config.mjs`.
Rewrites are resolved when the server starts in dev and **baked in at
`next build`**, so set `BACKEND_URL` at build time for production
(e.g. `BACKEND_URL=http://backend:8000 npm run build`).

Product guardrails enforced in the UI: no points, XP, streaks, badges,
leaderboards or urgency copy; the student can always end a session, and the
tutor match can be overridden on the onboarding screen.
