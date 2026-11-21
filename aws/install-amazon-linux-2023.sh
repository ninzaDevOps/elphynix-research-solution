#!/bin/bash
set -euo pipefail

# Run on a fresh Amazon Linux 2023 EC2 instance through SSM Run Command.
sudo dnf install -y python3.12 python3.12-pip nginx rsync curl tar
sudo install -d -o ec2-user -g ec2-user -m 0750 /opt/elphynix-research
sudo systemctl enable nginx

echo "Base packages installed. Upload/extract the application, configure /opt/elphynix-research/.env, then install the systemd and Nginx files."
