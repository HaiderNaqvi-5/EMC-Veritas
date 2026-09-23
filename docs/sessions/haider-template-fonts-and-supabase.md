# Haider template fonts and Supabase alignment

## Status

COMPLETE

## Objective

Complete the V1 uploaded-font requirement for certificate templates and verify that the connected Supabase schema and private storage configuration match the application.

## Completed work

- Corrected the leadership-template migration so it references the existing PostgreSQL enum rather than recreating it.
- Applied and verified the complete Alembic chain in Supabase, including fixed societies, leadership documents, template field styles, and the template-font schema.
- Confirmed the private `emc-veritas` bucket accepts allowed PDF, PNG/JPEG, TTF, and OTF asset types. A private PDF upload/download/delete smoke test passed.
- Added private, template-scoped TTF/OTF upload and listing APIs for Super Admins.
- Added custom-font selection to template field configuration. The server validates ownership and snapshots the font storage key into immutable field configuration.
- Extended the visual template editor with TTF/OTF upload and per-field custom-font selection.
- Extended PDF preview and issued-document rendering to embed uploaded custom fonts. Bundled Helvetica, Times Roman, and Courier remain available.

## Technical decisions

- Uploaded font assets use the existing Supabase Storage abstraction under a template-specific private key; no durable asset uses local Render disk.
- Field configurations store the selected font storage key rather than a mutable UI-only name, preserving rendering behavior for an issued document.
- Supabase's current `sb_secret_` key format authenticates through the `apikey` header; the adapter's combined headers remain compatible with current and legacy server credentials.

## PRD references

- Haider PRD §2, §3, §4, and §8.
- Project Rules §8, §9, §12, §13, and §14.

## Verification

- Live Alembic revision: `edb2eefdb003`.
- `alembic check`: no schema drift.
- Custom TTF embedding renderer test passes.
- Focused template/document tests: 21 passed.
- Full repository gate: 74 backend tests passed; frontend production build passed.

## Known issues and next step

- Render and Cloudflare deployment configuration/testing are intentionally deferred until Ahmed completes his assigned acceptance work, per the shared delivery instruction.
- Next: complete a requirement-by-requirement Haider audit and retain deployment as the final joint step.
