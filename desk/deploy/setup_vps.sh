#!/usr/bin/env bash
# desk/deploy/setup_vps.sh — provision the desk on a fresh Ubuntu ARM VPS.
# Target: Oracle Cloud Always Free (4 ARM / 24 GB, $0) — Hetzner CAX11 ($3.79/mo) fallback.
# Idempotent: safe to re-run. FAKE MONEY ONLY — installs no wallet/keys.
set -euo pipefail

REPO_DIR="${HOME}/polymarket"

echo "==> system deps"
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

echo "==> python deps (stdlib-only core; prefect/anthropic optional)"
python3 -m pip install --user --upgrade pip
# Core desk + papertrader run on the stdlib. These are only needed to go live:
python3 -m pip install --user prefect anthropic || true

echo "==> kernel baseline + self-test (must pass before scheduling anything)"
cd "${REPO_DIR}"
python3 -m desk.kernel.invariants --rebaseline
for t in test_kernel test_memory test_brief test_risk test_backtest test_selfmod test_cycle; do
  python3 "desk/tests/${t}.py"
done

echo "==> install systemd user timers (run without root, survive reboot)"
mkdir -p "${HOME}/.config/systemd/user"
cp desk/deploy/papertrader-scan.service "${HOME}/.config/systemd/user/"
cp desk/deploy/papertrader-scan.timer   "${HOME}/.config/systemd/user/"
cp desk/deploy/desk-cycle.service       "${HOME}/.config/systemd/user/"
cp desk/deploy/desk-cycle.timer         "${HOME}/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now papertrader-scan.timer
systemctl --user enable --now desk-cycle.timer
# let user services keep running after logout
sudo loginctl enable-linger "$(whoami)" || true

echo "==> done. Status:"
systemctl --user list-timers --all | grep -E 'papertrader|desk' || true
cat <<'NOTE'

Next (the two human steps):
  1. To switch the LLM from mock -> real, create desk/.env with:
       DESK_LLM=claude
       ANTHROPIC_API_KEY=sk-ant-...
     (keys live ONLY in this env file, never in config.json — see kernel rules.)
  2. To allow autonomous self-modification, edit desk/selfmod_config.json and set
     "self_modification_enabled": true  AFTER you have >=30 resolved bets and have
     watched a few digests. It is OFF by default.

The reactive scan + reflective cycle now run on schedule, laptop-independent.
NOTE
