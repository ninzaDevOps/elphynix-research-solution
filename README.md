# Elphynix Research Solution

Flask + MySQL research/survey application, prepared for manual deployment to private AWS EC2 instances.

## Included features

- Flask web application with Jinja templates
- Admin login using password hashes and an HttpOnly session cookie
- CSRF protection for browser POST/PUT requests
- Project creation and listing
- Client and vendor management APIs
- Survey completion, termination, quota-full and security-termination links
- Analytics metrics and traffic chart
- Request logging and health endpoints
- Nginx reverse proxy and systemd service files for Amazon Linux 2023
- Manual deployment script suitable for execution through AWS Systems Manager Run Command

## 1. Prerequisites

- Python 3.12
- MySQL 8.0 or compatible MySQL server
- Git
- Windows PowerShell, Linux shell, or macOS Terminal

## 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For Linux production EC2, install `requirements-prod.txt` instead; it adds Gunicorn. Gunicorn is not used for Windows local development.

## 3. Configure MySQL

Run the SQL scripts in order:

```text
database/01_create_database.sql
database/02_schema.sql
database/03_seed_data.sql
```

Before running the seed file, generate a Werkzeug password hash and replace both `CHANGE_ME_WERKZEUG_HASH` placeholders. Instructions and the least-privilege local database user SQL are in `database/README.md`.

## 4. Configure environment variables

Copy `.env.example` to `.env` and replace all `CHANGE_ME` values. Generate independent secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Run this command twice: once for `FLASK_SECRET_KEY`, and once for `JWT_SECRET`. Set the MySQL host, username and password. Never commit `.env`.

For local development, use `COOKIE_SECURE=false`. For the HTTPS production site, set `COOKIE_SECURE=true`.

## 5. Run locally

```bash
python app.py
```

Open `http://127.0.0.1:5000/login`.

Survey callback URLs must include the project identifier, respondent UID and the random `projectToken` returned when the project is created. Example: `/survey/complete?pid=PROJECT-ID&uid=RESPONDENT-ID&token=PROJECT-TOKEN`. The token is checked before a response status can be changed.

The application listens on loopback for local use. For production, Gunicorn listens on `127.0.0.1:5000` and Nginx listens on port 80; the EC2 security group should allow port 80 only from the internal ALB security group.

## 6. Test endpoints

Unauthenticated health endpoints:

- `GET /health/live` — process liveness; does not depend on the database.
- `GET /health/ready` — database readiness; configure the ALB target group to use this path.

After login, the UI uses the session cookie for authenticated API calls.

## 7. Manual Git workflow

```bash
git init
git add .
git commit -m "Prepare Elphynix application for deployment"
```

Create a private GitHub repository, then add its remote and push. Do not commit `.env`, database passwords, private keys or real password hashes.

## 8. AWS deployment outline — no Terraform or CI/CD

1. Create the VPC and private application/database subnets in two Availability Zones through the AWS Console.
2. Create the EC2 instance role with Systems Manager permissions and configure the required SSM VPC endpoints if the instance has no NAT route.
3. Launch Amazon Linux 2023 EC2 instances without public IP addresses.
4. Use Session Manager to administer the instances; do not open SSH to the internet.
5. Place the application in `/opt/elphynix-research`, configure its `.env` file securely, and install Nginx/systemd using the files under `aws/`.
6. Create private RDS MySQL and apply the database schema.
7. Create an internal ALB across the two public/private-designated application subnets as appropriate for the chosen CloudFront VPC Origin design; target EC2 on port 80 and use `/health/ready` as the health check.
8. Configure CloudFront VPC Origin, ACM and Route 53 for browser access. Keep EC2 and RDS private.
9. Deploy new application releases manually: create a release archive, upload it to a private S3 bucket, then invoke `aws/deploy.sh` through SSM Run Command on the target instance(s).

The deploy script installs `requirements-prod.txt` on Linux. It expects a `.tar.gz` archive whose top level contains `app.py`, `requirements.txt`, `requirements-prod.txt`, `templates/`, `static/` and `aws/`. It preserves the instance `.env` and `.venv` directories. From the project root, create a release archive with:

```bash
tar -czf elphynix-release.tar.gz --exclude='.git' --exclude='.venv' --exclude='__pycache__' --exclude='.env' .
```

Upload the archive to a private S3 bucket, then use SSM Run Command to run `aws/deploy.sh /path/to/elphynix-release.tar.gz` on the instance. Ensure `/opt/elphynix-research/.env` exists before deployment. Test deployment on one instance before rolling it across the Auto Scaling Group.

## 9. Production security notes

- Store RDS credentials and Flask/JWT secrets in AWS Secrets Manager or securely injected instance configuration; do not store them in Git.
- Set `COOKIE_SECURE=true` behind HTTPS.
- Use a dedicated least-privilege RDS application user.
- Keep EC2 and RDS without public IP/public accessibility.
- Allow EC2 inbound HTTP only from the ALB security group.
- Allow RDS inbound MySQL only from the EC2 application security group.
- Use SSM Session Manager instead of SSH.
- The demo seed accounts and data are for local validation only; change credentials and remove demo data before production.

## Known scope

This repository is the Flask project present in the supplied ZIP. It is not the original Spring Boot source tree. The project is a starter implementation; review business rules, authorization roles, data retention, privacy requirements and load behavior before production use.
