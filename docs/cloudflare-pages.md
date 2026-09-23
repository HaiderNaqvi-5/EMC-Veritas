# Cloudflare Pages release configuration

Deploy the `frontend` directory as a Cloudflare Pages project.

- Build command: `npm run build`
- Build output directory: `dist`
- Production environment variable: `VITE_API_BASE_URL=https://<render-api-host>/api`

The bundled `_redirects` file preserves React Router deep links, and `_headers` keeps versioned static assets cacheable. The UI renders before the API is available; it warms `/api/health/ready` in the background and preserves user input during a Render cold start.

Before production release, set Render's `FRONTEND_ORIGINS` to the exact Cloudflare Pages origin and `PUBLIC_APP_URL` to the public Pages URL. Verify the public API is HTTPS and that cookie settings work across those origins.
