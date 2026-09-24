# A3 — Public verification experience

- Added `/verify`, a student- and third-party-facing verification entry page that accepts a document verification ID.
- The page routes to the existing authoritative `/verify/:verificationId` record lookup; no duplicate client-side verification logic was introduced.
- Redesigned loading, failure, and verified-record states to match the public EMC Veritas visual system.
- Landing-page verification links now lead to the standalone verification workflow.
