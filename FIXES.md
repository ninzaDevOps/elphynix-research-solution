# Pre-deployment fixes applied

This package is a repaired working baseline based on the uploaded Flask ZIP. It is not a claim of end-to-end testing against a live MySQL server or AWS account.

## Application and database contract

- Replaced the inconsistent pluralized SQL schema with the singular table names actually used by the Flask routes: `client`, `project`, and `survey_response`.
- Added all fields used by project, vendor, client, survey, analytics, and request-log queries.
- Added foreign keys and indexes for project/client relationships, survey callbacks, status filtering, and request history.
- Corrected analytics and survey queries to use the schema's `survey_response.start_time` and other defined columns.
- Made survey callbacks require a cryptographically random project callback token. The project creation API returns `projectToken`; include it in survey callback URLs.

## Application security and operations

- Removed built-in fallback Flask/JWT secrets and default database password; app startup now requires configured secrets and DB password.
- Changed browser authentication to an HttpOnly session cookie instead of storing the JWT in localStorage.
- Added CSRF protection for browser POST/PUT requests.
- Added input validation for project, vendor, client, and password operations.
- Changed `/health/live` to a process-only liveness check and added `/health/ready` for database readiness; use `/health/ready` for the ALB target group.
- Replaced detailed exception responses with generic client errors and server-side logging.
- Added request timing and best-effort request logging.

## Frontend and deployment

- Removed the external Chart.js CDN dependency; the analytics page now draws its chart with browser canvas APIs.
- Replaced unsafe dynamic HTML insertion in the projects table with DOM text nodes.
- Added a production Gunicorn requirements file, systemd service, Nginx config, Amazon Linux 2023 package installer, and manual deployment/health-check script.
- Added `.gitignore` coverage for environment files, private keys, logs, and Python build artifacts.

## Validation performed in this environment

- Python source compilation passed (`python -m compileall`).
- JavaScript syntax checks passed (`node --check`).
- Static consistency review performed across Flask SQL statements and the supplied schema.
- A live MySQL integration test, browser login test, and AWS deployment test were not run here because no MySQL server or AWS account connection is available in this environment. Run the local verification steps in `README.md` before deploying.
