#!/bin/bash
set -euo pipefail

APP_DIR="/opt/elphynix-research"
ARCHIVE="${1:?Usage: deploy.sh /path/to/elphynix-release.tar.gz}"
STAGING="$(mktemp -d)"
BACKUP="${APP_DIR}.previous"

cleanup() { rm -rf "$STAGING"; }
trap cleanup EXIT

if [[ ! -f "$ARCHIVE" ]]; then
  echo "Release archive not found: $ARCHIVE" >&2
  exit 1
fi

tar -xzf "$ARCHIVE" -C "$STAGING"
if [[ ! -f "$STAGING/app.py" || ! -f "$STAGING/requirements.txt" ]]; then
  echo "Archive must contain app.py and requirements.txt at its root." >&2
  exit 1
fi

sudo systemctl stop elphynix-research || true
sudo rm -rf "$BACKUP"
if [[ -d "$APP_DIR" ]]; then sudo cp -a "$APP_DIR" "$BACKUP"; fi
sudo rsync -a --delete --exclude='.env' --exclude='.venv' "$STAGING/" "$APP_DIR/"
sudo chown -R ec2-user:ec2-user "$APP_DIR"
sudo -u ec2-user python3.12 -m venv "$APP_DIR/.venv"
sudo -u ec2-user "$APP_DIR/.venv/bin/pip" install --upgrade pip
sudo -u ec2-user "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements-prod.txt"
sudo install -m 0644 "$APP_DIR/aws/elphynix-research.service" /etc/systemd/system/elphynix-research.service
sudo install -m 0644 "$APP_DIR/aws/nginx.conf" /etc/nginx/conf.d/elphynix-research.conf
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable nginx elphynix-research
sudo systemctl restart nginx elphynix-research

for attempt in {1..20}; do
  if curl --fail --silent http://127.0.0.1/health/ready >/dev/null; then
    echo "Deployment successful."
    exit 0
  fi
  sleep 3
done

echo "Health check failed. Attempting rollback." >&2
sudo systemctl stop elphynix-research || true
if [[ -d "$BACKUP" ]]; then
  sudo rsync -a --delete --exclude='.env' --exclude='.venv' "$BACKUP/" "$APP_DIR/"
  sudo chown -R ec2-user:ec2-user "$APP_DIR"
  sudo systemctl daemon-reload
  sudo systemctl restart nginx elphynix-research || true
fi
echo "Deployment failed. Check: journalctl -u elphynix-research -n 100" >&2
exit 1
