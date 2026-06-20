#!/usr/bin/env bash
# setup_gcp.sh — Deploy PaperTrader to GCP e2-micro (free tier)
#
# Prerequisites (run once on your local machine):
#   1. Create a GCP account at console.cloud.google.com
#   2. Create a new project (e.g. "papertrader")
#   3. Enable the Compute Engine API for that project
#   4. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
#   5. Run: gcloud auth login && gcloud config set project YOUR_PROJECT_ID
#
# Usage:
#   chmod +x setup_gcp.sh
#   ./setup_gcp.sh          # first run: creates VM + deploys
#   ./setup_gcp.sh --push   # subsequent runs: git push to VM only
#
# The e2-micro instance runs in the free tier (1 vCPU, 1GB RAM, 30GB disk,
# us-east1/us-west1/us-central1 region only). Scans run every 30min via cron.

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-papertrader}"
ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE_NAME="papertrader-desk"
MACHINE_TYPE="e2-micro"
IMAGE_FAMILY="debian-12"
IMAGE_PROJECT="debian-cloud"
DISK_SIZE="20GB"
REPO_DIR="/home/papertrader/polymarket"

# ── step 1: create VM (skip if already exists) ────────────────────────────────
echo "==> Checking for existing VM..."
if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
    echo "    VM '$INSTANCE_NAME' already exists. Skipping creation."
else
    echo "==> Creating e2-micro VM in $ZONE..."
    gcloud compute instances create "$INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --zone="$ZONE" \
        --machine-type="$MACHINE_TYPE" \
        --image-family="$IMAGE_FAMILY" \
        --image-project="$IMAGE_PROJECT" \
        --boot-disk-size="$DISK_SIZE" \
        --boot-disk-type="pd-standard" \
        --tags="papertrader" \
        --metadata=startup-script='#!/bin/bash
apt-get update -y
apt-get install -y python3 python3-pip git
useradd -m -s /bin/bash papertrader || true
'
    echo "    VM created. Waiting 30s for startup script..."
    sleep 30
fi

# ── step 2: set up SSH key if needed ─────────────────────────────────────────
if [ ! -f ~/.ssh/gcp_papertrader ]; then
    echo "==> Generating SSH key..."
    ssh-keygen -t ed25519 -f ~/.ssh/gcp_papertrader -N "" -C "papertrader@gcp"
    gcloud compute os-login ssh-keys add --key-file=~/.ssh/gcp_papertrader.pub \
        --project="$PROJECT_ID" || true
fi

EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" \
    --zone="$ZONE" --project="$PROJECT_ID" \
    --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

echo "==> VM external IP: $EXTERNAL_IP"

SSH="ssh -i ~/.ssh/gcp_papertrader -o StrictHostKeyChecking=no papertrader@$EXTERNAL_IP"
SCP="scp -i ~/.ssh/gcp_papertrader -o StrictHostKeyChecking=no"

# ── step 3: push code ─────────────────────────────────────────────────────────
echo "==> Syncing code to VM..."
rsync -avz --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='data/scans/' \
    -e "ssh -i ~/.ssh/gcp_papertrader -o StrictHostKeyChecking=no" \
    "$(dirname "$0")/papertrader/" \
    "papertrader@$EXTERNAL_IP:$REPO_DIR/papertrader/"

# ── step 4: install Python deps ───────────────────────────────────────────────
echo "==> Installing dependencies..."
$SSH "pip3 install --user openpyxl requests 2>/dev/null || true"

# ── step 5: set up cron (scan every 30min, settle every hour) ─────────────────
echo "==> Installing cron jobs..."
CRON=$(cat <<CRONTAB
# PaperTrader — scan every 30min, settle hourly, weekly digest Sunday 9am UTC
*/30 * * * * cd $REPO_DIR && python3 papertrader/papertrader.py scan >> papertrader/logs/cron_scan.log 2>&1
0 * * * *   cd $REPO_DIR && python3 papertrader/papertrader.py settle >> papertrader/logs/cron_settle.log 2>&1
0 9 * * 0   cd $REPO_DIR && python3 papertrader/papertrader.py weekly >> papertrader/logs/cron_weekly.log 2>&1
CRONTAB
)
$SSH "mkdir -p $REPO_DIR/papertrader/logs && echo '$CRON' | crontab -"

echo ""
echo "==> Deploy complete!"
echo "    VM:      $INSTANCE_NAME ($EXTERNAL_IP)"
echo "    SSH:     ssh -i ~/.ssh/gcp_papertrader papertrader@$EXTERNAL_IP"
echo "    Logs:    $REPO_DIR/papertrader/logs/"
echo "    Status:  ssh ... 'cd $REPO_DIR && python3 papertrader/papertrader.py status'"
echo ""
echo "    To push code updates later: ./setup_gcp.sh --push"
echo "    To stop the VM:  gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE"
echo "    To start it:     gcloud compute instances start $INSTANCE_NAME --zone=$ZONE"
echo "    Cost:            \$0/month in free tier (us-central1, < 744 hrs/mo)"
