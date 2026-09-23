# Haider document lifecycle

## Status

COMPLETE SERVICE FOUNDATION

## Delivered

- Added a PyMuPDF renderer that overlays configured, one-based PDF field coordinates onto an uploaded template.
- Requires the certificate fields `student_name`, `roll_number`, `activity_name`, and `activity_date`; an optional `qr_code` field receives the immutable verification URL QR image.
- Added a first-download lifecycle: valid documents are rendered once, uploaded to the private Supabase Storage bucket, SHA-256 hashed, and then served from the same stored object on later downloads.
- Invalid, revoked, and superseded documents cannot trigger a render or a normal download.
- Added test coverage for render, cache, hash, audit event, and invalid-document rejection.

## Integration contract

The secured Haider-owned issuance/download route must load the approved template and its `TemplateField` records, build the certificate values, and call `generate_on_first_download`. It must not render or upload a document for a non-`VALID` record.

## Deliberately not included

Admin UI for template field placement and the operational route/auth wiring remain separate work. This service does not replace a supplied PDF template with a newly-created certificate.
