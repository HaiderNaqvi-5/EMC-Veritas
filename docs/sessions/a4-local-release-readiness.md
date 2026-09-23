# A4 local release readiness

## Local checks completed

- Student roll-number lookup preserves input and renders a data-area skeleton while records load.
- Recognized Admins receive a password prompt; ordinary students do not.
- Expired Admin sessions return to the landing page.
- Temporary Admin passwords must be changed before normal Admin use.
- Admin mutation actions do not auto-retry; safe GET requests use bounded retry behavior.
- Public verification renders an authoritative-record loading skeleton.
- Admin workflows cover students, sessions, activities, eligibility, imports, exports, signatories, templates, document actions, audit access, and leadership-template UI foundation.

## Required final joint/deployed checks

These checks must be run after Haider’s remaining server contracts and deployed environments are available:

1. Import participants, configure an approved template and required signatories, issue an activity, download as the student, and verify the same document publicly.
2. Verify revoked and superseded document results through both manual and QR verification paths.
3. Verify Super Admin-only leadership-template management and automatic session-end recognition.
4. Test Render cold start with a slow backend: no blank shell, lost roll number, duplicate action, or false empty result.
5. Check deployed Cloudflare Pages and Render URLs against Supabase Storage/PostgreSQL using production-safe environment values.

No deployment, push, or environment mutation is part of this local A4 work.
