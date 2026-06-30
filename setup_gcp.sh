#!/usr/bin/env bash
# setup_gcp.sh — Deploy PaperTrader + Desk to a GCP e2-micro (free tier).
# FAKE MONEY ONLY — installs no wallet/keys.
#
# ─── WHY THIS IS SSH-FREE ─────────────────────────────────────────────────────
# Earlier versions used `gcloud compute ssh`, which on Windows routes through
# PuTTY's plink and broke in a dozen ways (plink rejects -o flags, .ppk missing,
# OS Login username mismatch, host-key prompts, key-overwrite aborts). So this
# version does ZERO interactive SSH. Instead:
#   • the VM runs a STARTUP SCRIPT (as root) that installs everything itself;
#   • it prints its git deploy key to the SERIAL CONSOLE;
#   • we read that with `gcloud ... get-serial-port-output` (no SSH);
#   • the VM clones the repo and pushes results back to GitHub over its own key.
# Nothing on your Windows box ever opens an SSH connection. plink can't bite us.
#
# ─── ONE-TIME PREREQUISITES (local) ───────────────────────────────────────────
#   1. GCP account + project (already done: friendly-anthem-500014-q7).
#   2. Compute Engine API enabled (already done).
#   3. gcloud CLI installed + `gcloud auth login`.
#
# ─── USAGE ────────────────────────────────────────────────────────────────────
#   bash setup_gcp.sh            # create/refresh VM, print the deploy key
#   <add the printed key to GitHub → Settings → Deploy keys → Allow write access>
#   bash setup_gcp.sh --finish   # reboot VM so it clones + schedules cron
#   bash setup_gcp.sh --status   # verify (no SSH): serial tail + last bot commit
#
# IMPORTANT: once GCP is confirmed pushing commits, DISABLE the GitHub Actions
# schedule (comment out `schedule:` in .github/workflows/desk-scan.yml and
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
GIT_USER_NAME="papertrader-gcp"
GIT_USER_EMAIL="desk-bot@users.noreply.github.com"

g() { gcloud "$@" --project="$PROJECT_ID"; }

serial() {
    g compute instances get-serial-port-output "$INSTANCE_NAME" \
        --zone="$ZONE" --port=1 2>/dev/null || true
}

# ── build the VM startup script (runs as root on every boot, idempotent) ───────
# Config values are injected via a real-assignment preamble (expanded locally);
# the quoted body keeps cron's % and $(date) literal for the VM to evaluate.
build_startup() {
    local f; f="$(mktemp)"
    {
        echo '#!/bin/bash'
        echo "REPO_SSH='$REPO_SSH'"
        echo "GIT_USER_NAME='$GIT_USER_NAME'"
        echo "GIT_USER_EMAIL='$GIT_USER_EMAIL'"
        cat <<'STARTUP'
# ---- everything below runs on the VM, as root, on each boot ----
REPO_DIR=/root/polymarket
PYBIN=/root/ptenv/bin/python3
# The GCE startup runner executes as root but with NO $HOME — git --global and
# git's SSH config both need it. Set it explicitly.
export HOME=/root
# Tee to a log AND to stdout — GCE only mirrors startup-script *stdout* to the
# serial console, which is how this script reads the deploy key (no SSH).
exec > >(tee -a /var/log/papertrader-setup.log) 2>&1
echo "=====PAPERTRADER_SETUP_START $(date -u +%FT%TZ)====="

# 1. deploy key FIRST (no apt needed) so it always reaches the serial console
mkdir -p /root/.ssh && chmod 700 /root/.ssh
[ -f /root/.ssh/id_ed25519 ] || ssh-keygen -t ed25519 -f /root/.ssh/id_ed25519 -N "" -C papertrader-gcp
grep -q github.com /root/.ssh/known_hosts 2>/dev/null || ssh-keyscan github.com >> /root/.ssh/known_hosts 2>/dev/null
echo "=====DEPLOY_KEY_BEGIN====="
cat /root/.ssh/id_ed25519.pub
echo "=====DEPLOY_KEY_END====="

# 2. system packages
apt-get update -y || true
apt-get install -y python3 python3-pip python3-venv git || true

# 3. git identity + clone/pull (clone fails until the deploy key is on GitHub —
#    that's fine; --finish reboots to retry, and cron retries every 30 min)
git config --global user.name "$GIT_USER_NAME"
git config --global user.email "$GIT_USER_EMAIL"
if [ -d "$REPO_DIR/.git" ]; then
    # Use the wedge-proof sync if it's already checked out; fall back otherwise.
    cd "$REPO_DIR" && (bash desk/deploy/vm_sync.sh 2>/dev/null || git pull --rebase --autostash || true)
    echo "=====CLONE_OK====="
else
    # a previous partial run may have left a non-git dir — clear it so clone works
    rm -rf "$REPO_DIR"
    if git clone "$REPO_SSH" "$REPO_DIR"; then
        echo "=====CLONE_OK====="
    else
        echo "=====CLONE_FAILED_ADD_DEPLOY_KEY_THEN_RERUN_FINISH====="
    fi
fi

# 4. python venv (Debian 12 is PEP-668 'externally managed' — venv avoids the
#    pip refusal; --system-site-packages keeps stdlib + apt modules visible)
[ -d /root/ptenv ] || python3 -m venv --system-site-packages /root/ptenv
if [ -f "$REPO_DIR/desk/requirements.txt" ]; then
    /root/ptenv/bin/pip install --upgrade pip >/dev/null 2>&1 || true
    /root/ptenv/bin/pip install -r "$REPO_DIR/desk/requirements.txt" || true
fi

# 5. cron (mirrors GitHub Actions). Single-quoted heredoc → % and $(date) stay
#    literal for cron; absolute python/paths so no PATH surprises. export_state
#    is wrapped in || true so a missing module never blocks the commit+push.
mkdir -p /root/polymarket/papertrader/logs
cat > /etc/cron.d/papertrader <<'CRON'
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
# scan + settle every 30 min, snapshot data back to git
*/30 * * * * root cd /root/polymarket && bash desk/deploy/vm_sync.sh && (cd papertrader && /root/ptenv/bin/python3 papertrader.py scan && /root/ptenv/bin/python3 papertrader.py settle) && (/root/ptenv/bin/python3 -m desk.export_state || true) && git add papertrader/data desk/memory/lessons desk/dashboard_state.json && git commit -m "auto(gcp-scan): $(date -u +\%FT\%TZ)" && git push >> /root/polymarket/papertrader/logs/cron_scan.log 2>&1
# institute: crypto-daily live sensor, offset minutes so it NEVER shares a push
# tick with the scan line above (isolated failure domain -- an institute hiccup
# can never wedge the proven papertrader pipeline). Captures live q while markets
# are OPEN (irreplaceable decision-time prior), settles y once they close, and
# persists the append-only market stores to git so a VM rebuild keeps the history.
5,35 * * * * root cd /root/polymarket && bash desk/deploy/vm_sync.sh && /root/ptenv/bin/python3 -m institute.cli crypto-snapshot && /root/ptenv/bin/python3 -m institute.cli forecast && /root/ptenv/bin/python3 -m institute.cli crypto-settle && git add institute/data && (git diff --cached --quiet || (git commit -m "auto(institute): $(date -u +\%FT\%TZ)" && git push)) >> /root/polymarket/papertrader/logs/cron_institute.log 2>&1
# reflective desk cycle daily 14:15 UTC
15 14 * * * root cd /root/polymarket && bash desk/deploy/vm_sync.sh && /root/ptenv/bin/python3 -m desk.run_cycle && (/root/ptenv/bin/python3 -m desk.export_state || true) && git add desk/memory desk/dashboard_state.json && git commit -m "auto(gcp-cycle): $(date -u +\%FT\%TZ)" && git push >> /root/polymarket/papertrader/logs/cron_cycle.log 2>&1
# B1: CPI macro-nowcasting vertical -- daily at 12:20 UTC (CPI is monthly; daily
# re-run picks up newly-listed markets; idempotent on already-snapshotted ones).
# snapshot freezes p_model from free BLS/FRED data; settle fills y after BLS release.
20 12 * * * root cd /root/polymarket && bash desk/deploy/vm_sync.sh && /root/ptenv/bin/python3 -m institute.cli cpi-snapshot && /root/ptenv/bin/python3 -m institute.cli cpi-settle && git add institute/data && (git diff --cached --quiet || (git commit -m "auto(cpi): $(date -u +\%FT\%TZ)" && git push)) >> /root/polymarket/papertrader/logs/cron_institute.log 2>&1
# weekly digest Sunday 09:00 UTC
0 9 * * 0 root cd /root/polymarket/papertrader && /root/ptenv/bin/python3 papertrader.py weekly >> logs/cron_weekly.log 2>&1
CRON
chmod 0644 /etc/cron.d/papertrader
echo "=====PAPERTRADER_SETUP_DONE $(date -u +%FT%TZ)====="
STARTUP
    } > "$f"
    echo "$f"
}

# ── apply startup script to VM + (re)boot it so the script runs ───────────────
apply_and_boot() {
    local sf; sf="$(build_startup)"
    if g compute instances describe "$INSTANCE_NAME" --zone="$ZONE" &>/dev/null; then
        echo "==> VM exists — updating startup script + rebooting to run it..."
        g compute instances add-metadata "$INSTANCE_NAME" --zone="$ZONE" \
            --metadata-from-file startup-script="$sf"
        g compute instances reset "$INSTANCE_NAME" --zone="$ZONE"
    else
        echo "==> Creating e2-micro VM in $ZONE (free tier)..."
        g compute instances create "$INSTANCE_NAME" \
            --zone="$ZONE" \
            --machine-type="$MACHINE_TYPE" \
            --image-family="$IMAGE_FAMILY" \
            --image-project="$IMAGE_PROJECT" \
            --boot-disk-size="$DISK_SIZE" \
            --boot-disk-type="pd-standard" \
            --tags="papertrader" \
            --metadata-from-file startup-script="$sf"
    fi
    rm -f "$sf"
    local ip
    ip="$(g compute instances describe "$INSTANCE_NAME" --zone="$ZONE" \
          --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
    echo "==> VM external IP: $ip"
}

# ── poll the serial console for a marker; print captured block ────────────────
# wait_for <BEGIN_MARKER> <END_MARKER> <max_polls>  → echoes block between markers
wait_for() {
    local begin="$1" end="$2" max="$3" i out block
    for ((i=1; i<=max; i++)); do
        out="$(serial)"
        block="$(printf '%s\n' "$out" | awk -v b="$begin" -v e="$end" '
            $0 ~ b {c=1; val=""; next}
            $0 ~ e {c=0; last=val}
            c {val=val $0 "\n"}
            END {printf "%s", last}')"
        if [ -n "$block" ]; then printf '%s' "$block"; return 0; fi
        sleep 15
    done
    return 1
}

# ── poll for a single marker line existing in serial output ───────────────────
wait_marker() {
    local marker="$1" max="$2" i
    for ((i=1; i<=max; i++)); do
        if serial | grep -q "$marker"; then return 0; fi
        sleep 15
    done
    return 1
}

case "${1:-}" in
# ── --status: verify with NO SSH ─────────────────────────────────────────────
--status)
    g compute instances list --filter="name=$INSTANCE_NAME"
    echo "── last serial lines ─────────────────────────────────"
    serial | tail -n 20
    echo "── last bot commit on origin ─────────────────────────"
    git fetch -q origin 2>/dev/null || true
    git log origin/master -1 --format='%h  %an  %ar  %s' 2>/dev/null \
        || echo "(could not read origin/master)"
    exit 0
    ;;

# ── --finish: reboot so the VM clones (deploy key now on GitHub) + verify ─────
--finish)
    apply_and_boot
    echo "==> Rebooted. Waiting for the VM to clone the repo (up to ~10 min)..."
    if wait_marker "CLONE_OK" 40; then
        echo ""
        echo "==> ✅ Deploy complete — VM cloned the repo and scheduled cron."
        echo "    Cron: scan/settle every 30 min, cycle daily 14:15 UTC, digest Sun 09:00 UTC."
        echo "    Verify anytime:  bash setup_gcp.sh --status"
        echo "    NEXT: disable the GitHub Actions schedule so the two don't both push."
    else
        echo ""
        echo "==> ⚠️  Did not see CLONE_OK yet. Most likely the deploy key isn't added"
        echo "    (or lacks write access). Check the serial tail below, fix, re-run --finish:"
        serial | tail -n 25
        exit 1
    fi
    exit 0
    ;;

# ── default: create/refresh VM, print the deploy key ─────────────────────────
"")
    apply_and_boot
    echo "==> Waiting for the VM to generate + print its deploy key (up to ~10 min)..."
    if KEYBLOCK="$(wait_for 'DEPLOY_KEY_BEGIN' 'DEPLOY_KEY_END' 40)"; then
        # serial lines carry a syslog prefix, so extract just the key with grep -o
        KEY="$(printf '%s' "$KEYBLOCK" \
               | grep -oE 'ssh-ed25519 [A-Za-z0-9+/=]+ papertrader-gcp' | tail -1 || true)"
    fi
    if [ -z "${KEY:-}" ]; then
        echo "==> ⚠️  Could not read the deploy key from serial yet. Re-run in a minute:"
        echo "       bash setup_gcp.sh"
        exit 1
    fi
    echo ""
    echo "────────────────────────────────────────────────────────────────────"
    echo " ADD THIS AS A WRITE-ENABLED DEPLOY KEY ON GITHUB:"
    echo " Repo (${REPO_SSH}) → Settings → Deploy keys → Add deploy key"
    echo " → paste below, TICK \"Allow write access\", Save."
    echo ""
    echo "   $KEY"
    echo ""
    echo " Then run:  bash setup_gcp.sh --finish"
    echo "────────────────────────────────────────────────────────────────────"
    exit 0
    ;;

*)
    echo "usage: bash setup_gcp.sh [--finish|--status]" >&2
    exit 2
    ;;
esac
