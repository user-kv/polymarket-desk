#!/usr/bin/env bash
# setup_gcp.sh — Deploy PaperTrader + Desk to a GCP e2-micro (free tier).
#
# This is a GIT-BASED deploy: the VM clones the repo, and cron jobs pull,
# run, then commit+push results back — exactly mirroring the GitHub Actions
# pipeline (scan/settle every 30min, reflective cycle daily, weekly digest).
# That keeps data/scans/ (the backtest dataset) and the dashboard state in git.
# FAKE MONEY ONLY — installs no wallet/keys.
#
# ─── ONE-TIME PREREQUISITES (on your local machine) ───────────────────────────
#   1. Create a GCP account + project at console.cloud.google.com (e.g. "papertrader")
#   2. Enable the Compute Engine API for that project
#   3. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
#   4. Run: gcloud auth login && gcloud config set project YOUR_PROJECT_ID
#
# ─── GIT PUSH-BACK AUTH (required, one-time) ──────────────────────────────────
#   The VM must push commits back to GitHub. After the first run this script
#   prints an SSH public key — add it to your repo as a *Deploy key with write
#   access*:  GitHub repo → Settings → Deploy keys → Add deploy key → tick
#   "Allow write access". Re-run with --finish once the key is added.
#
# ─── USAGE ────────────────────────────────────────────────────────────────────
#   chmod +x setup_gcp.sh
#   ./setup_gcp.sh            # create VM, install, print the deploy key
#   ./setup_gcp.sh --finish   # after adding the deploy key: clone + schedule cron
#   ./setup_gcp.sh --status   # show VM + last cron log lines
#
# IMPORTANT: once GCP is confirmed running, DISABLE the GitHub Actions schedule
# (comment out the `schedule:` block in .github/workflows/desk-scan.yml and
# desk-cycle.yml) so the two don't both push and fight over the same files.

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-friendly-anthem-500014-q7}"   # display name: "papertrader"
ZONE="${GCP_ZONE:-us-central1-a}"
INSTANCE_NAME="papertrader-desk"
MACHINE_TYPE="e2-micro"
IMAGE_FAMILY="debian-12"
IMAGE_PROJECT="debian-cloud"
DISK_SIZE="20GB"
REPO_SSH="${REPO_SSH:-git@github.com:user-kv/polymarket-desk.git}"
# OS Login forces the SSH username to your Google account (e.g. kaveenkoho_gmail_com).
VM_USER="${GCP_VM_USER:-kaveenkoho_gmail_com}"
REPO_DIR="/home/$VM_USER/polymarket"
GIT_USER_NAME="papertrader-gcp"
GIT_USER_EMAIL="desk-bot@users.noreply.github.com"

SSH_KEY=~/.ssh/gcp_papertrader

# ── helper: resolve VM external IP ───────────────────────────────────────────
vm_ip() {
    gcloud compute instances describe "$INSTANCE_NAME" \
        --zone="$ZONE" --project="$PROJECT_ID" \
        --format="get(networkInterfaces[0].accessConfigs[0].natIP)"
}

# ── remote exec helper: gcloud handles the OS Login user + key propagation ────
gssh() {
    gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
        --quiet --ssh-flag="-o StrictHostKeyChecking=no" --command="$1"
}

# ── --status ─────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--status" ]]; then
    gcloud compute instances list --filter="name=$INSTANCE_NAME" --project="$PROJECT_ID"
    gssh "tail -n 15 $REPO_DIR/papertrader/logs/cron_scan.log 2>/dev/null || echo 'no scan log yet'"
    exit 0
fi

# ── step 1: create VM (skip if exists) ───────────────────────────────────────
echo "==> Checking for existing VM..."
if gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" &>/dev/null; then
    echo "    VM '$INSTANCE_NAME' already exists. Skipping creation."
else
    echo "==> Creating e2-micro VM in $ZONE (free tier)..."
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
apt-get install -y python3 python3-pip python3-venv git
useradd -m -s /bin/bash papertrader || true
'
    echo "    VM created. Waiting 30s for startup script..."
    sleep 30
fi

# ── step 2: pre-create gcloud's SSH key (no passphrase) so gssh runs unattended ─
if [ ! -f ~/.ssh/google_compute_engine ]; then
    echo "==> Generating SSH key for gcloud..."
    ssh-keygen -t rsa -b 2048 -f ~/.ssh/google_compute_engine -N "" -q -C "gcp-papertrader"
fi

IP=$(vm_ip)
echo "==> VM external IP: $IP"

# ── step 3: VM deploy key for git push-back ──────────────────────────────────
echo "==> Ensuring VM has a git deploy key (first connect may take ~30s)..."
gssh 'test -f ~/.ssh/id_ed25519 || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C papertrader-gcp'
DEPLOY_PUBKEY=$(gssh 'cat ~/.ssh/id_ed25519.pub' 2>/dev/null | grep '^ssh-ed25519')

if [[ "${1:-}" != "--finish" ]]; then
    echo ""
    echo "────────────────────────────────────────────────────────────────────"
    echo " ADD THIS AS A WRITE-ENABLED DEPLOY KEY ON GITHUB, THEN RE-RUN --finish"
    echo " GitHub repo → Settings → Deploy keys → Add deploy key (Allow write):"
    echo ""
    echo "   $DEPLOY_PUBKEY"
    echo ""
    echo " Then run:  ./setup_gcp.sh --finish"
    echo "────────────────────────────────────────────────────────────────────"
    exit 0
fi

# ── step 4 (--finish): clone repo + install deps ─────────────────────────────
echo "==> Cloning repo on VM (or pulling if present)..."
gssh "ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null; \
      git config --global user.name '$GIT_USER_NAME'; \
      git config --global user.email '$GIT_USER_EMAIL'; \
      if [ -d $REPO_DIR/.git ]; then cd $REPO_DIR && git pull --rebase --autostash; \
      else git clone $REPO_SSH $REPO_DIR; fi"

echo "==> Installing Python deps..."
gssh "pip3 install --user -r $REPO_DIR/desk/requirements.txt"

# ── step 5: cron — mirrors GitHub Actions (scan/settle 30min, cycle daily) ───
echo "==> Installing cron jobs..."
read -r -d '' CRON <<CRONTAB || true
# PaperTrader+Desk on GCP — FAKE MONEY ONLY. Pulls, runs, commits+pushes back.
SHELL=/bin/bash
# scan + settle every 30 min, then snapshot data back to git
*/30 * * * * cd $REPO_DIR && git pull --rebase --autostash -q && (cd papertrader && python3 papertrader.py scan && python3 papertrader.py settle) && python3 -m desk.export_state && git add papertrader/data desk/memory/lessons desk/dashboard_state.json && git commit -m "auto(gcp-scan): \$(date -u +\%FT\%TZ)" && git push >> papertrader/logs/cron_scan.log 2>&1
# reflective desk cycle once daily at 14:15 UTC
15 14 * * * cd $REPO_DIR && git pull --rebase --autostash -q && python3 -m desk.run_cycle && python3 -m desk.export_state && git add desk/memory desk/dashboard_state.json && git commit -m "auto(gcp-cycle): \$(date -u +\%FT\%TZ)" && git push >> papertrader/logs/cron_cycle.log 2>&1
# weekly digest Sunday 09:00 UTC
0 9 * * 0 cd $REPO_DIR/papertrader && python3 papertrader.py weekly >> logs/cron_weekly.log 2>&1
CRONTAB
gssh "mkdir -p $REPO_DIR/papertrader/logs && echo '$CRON' | crontab -"

echo ""
echo "==> Deploy complete!"
echo "    VM:      $INSTANCE_NAME ($IP)"
echo "    SSH:     gcloud compute ssh $INSTANCE_NAME --zone=$ZONE"
echo "    Logs:    $REPO_DIR/papertrader/logs/"
echo "    Status:  ./setup_gcp.sh --status"
echo ""
echo "    NEXT: disable the GitHub Actions schedule so the two don't both push."
echo "    Stop VM:  gcloud compute instances stop $INSTANCE_NAME --zone=$ZONE"
echo "    Start VM: gcloud compute instances start $INSTANCE_NAME --zone=$ZONE"
echo "    Cost:     \$0/month in free tier (us-central1, e2-micro, < 744 hrs/mo)"
