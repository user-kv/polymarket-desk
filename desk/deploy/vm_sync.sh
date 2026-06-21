#!/usr/bin/env bash
# vm_sync.sh — wedge-proof git sync for the GCP VM's cron pipeline.
#
# WHY: the cron chain used to begin with `git pull --rebase --autostash -q && ...`.
# If that pull hit ANY conflict (e.g. a tracked file deleted upstream but locally
# modified — a delete/modify "DU" conflict), the rebase aborted the whole && chain
# every 30 min and froze HEAD at a stale commit indefinitely. The VM looked healthy
# (RUNNING, cron active) while deploying nothing for ~8h on 2026-06-21.
#
# This script GUARANTEES the working tree ends on origin/master and NEVER leaves a
# half-finished rebase/merge behind. Worst case it preserves the current HEAD on a
# local recovery branch (no data loss) and snaps to origin. It is idempotent and
# safe to run every cron tick. It self-maintains: once on the VM, each tick updates
# this very file as part of the sync (the running copy is already in memory).
#
# Exit status is always 0 — a sync hiccup must never abort the caller's && chain.
set -uo pipefail
export HOME=/root
REPO_DIR="${REPO_DIR:-/root/polymarket}"
BRANCH="${SYNC_BRANCH:-master}"

cd "$REPO_DIR" 2>/dev/null || { echo "vm_sync: no repo at $REPO_DIR"; exit 0; }

log() { echo "vm_sync $(date -u +%FT%TZ): $*"; }

# Always clear any half-finished operation left by a prior crashed tick.
git rebase --abort  >/dev/null 2>&1 || true
git merge  --abort  >/dev/null 2>&1 || true
git cherry-pick --abort >/dev/null 2>&1 || true

if ! git fetch -q origin "$BRANCH"; then
    log "fetch failed (network?) — leaving tree as-is for this tick"
    exit 0
fi

local_head="$(git rev-parse HEAD 2>/dev/null || echo none)"
remote_head="$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo none)"

if [ "$local_head" = "$remote_head" ]; then
    exit 0   # already in sync, nothing to do
fi

# If we carry local commits NOT yet on origin (e.g. a push failed last tick),
# try to push them first so their data isn't discarded by the reset below.
if ! git merge-base --is-ancestor HEAD "origin/$BRANCH" 2>/dev/null; then
    if git push -q origin "HEAD:$BRANCH" 2>/dev/null; then
        log "pushed unsynced local commits to origin/$BRANCH"
        git fetch -q origin "$BRANCH" || true
        remote_head="$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo none)"
    fi
fi

# Try the clean path first: rebase local work onto origin (autostash data edits).
if git -c rebase.autostash=true rebase -q "origin/$BRANCH" >/dev/null 2>&1; then
    exit 0
fi

# Rebase failed (conflict = the wedge). Abort it and recover deterministically.
git rebase --abort >/dev/null 2>&1 || true
recovery="wedge-recovery-$(date -u +%Y%m%dT%H%M%SZ)"
git branch -f "$recovery" HEAD >/dev/null 2>&1 || true
git reset --hard -q "origin/$BRANCH"
log "WEDGE cleared: reset to origin/$BRANCH; prior HEAD saved on $recovery"
exit 0
