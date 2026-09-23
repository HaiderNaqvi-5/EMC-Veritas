# Cloudflare Pages release configuration

Deploy the `frontend` directory as a Cloudflare Pages project.

- Root directory: `frontend`
- Build command: `npm run build`
- Build output directory: `dist`
- Production environment variable: `VITE_API_BASE_URL=https://<render-api-host>/api`

The bundled `_redirects` file preserves React Router deep links, and `_headers` keeps versioned static assets cacheable. The UI renders before the API is available; it warms `/api/health/ready` in the background and preserves user input during a Render cold start.

Before production release, set these Render variables using the exact Cloudflare Pages origin (without a trailing slash):

- `FRONTEND_ORIGINS=https://<project>.pages.dev`
- `PUBLIC_APP_URL=https://<project>.pages.dev`
- `COOKIE_SECURE=true`
- `COOKIE_SAME_SITE=none`

`COOKIE_SAME_SITE=none` plus `COOKIE_SECURE=true` is required because the Pages site and Render API are different sites. Verify the public API is HTTPS and that an Admin session remains signed in after a page refresh.
