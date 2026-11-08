#!/usr/bin/env bash
# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
# Emergency SSH entry point and explicit host-service installer/upgrade launcher.
# Inspected v3's fixed paths, env, Git/image/storage preservation and failure flow.
# V4 delegates to ONE host engine shared with browser updates. It never sources
# .env, mounts Docker into Flask, runs initialization, or restores data silently.
set -Eeuo pipefail
umask 077
ROOT_DIR=/root/WorkoutTracker
ACTION=update
INSTALL_ARGS=()
ENGINE_ARGS=()
while (( $# )); do
    case "$1" in
        --root) [[ $# -ge 2 ]] || exit 2; ROOT_DIR=$2; shift 2 ;;
        --install-service|--upgrade-service) ACTION=install; shift ;;
        --lan-address|--app-url|--status-port) [[ $# -ge 2 ]] || exit 2; INSTALL_ARGS+=("$1" "$2"); shift 2 ;;
        --backup) shift ;; # Compatibility: every confirmed v4 update already verifies a backup.
        --confirm|--allow-migration) ENGINE_ARGS+=("$1"); shift ;;
        --check) ACTION=check; shift ;;
        --status) ACTION=status; shift ;;
        --help) printf '%s\n' 'Usage: update_workout_tracker_v4.sh [--root PATH] [--check|--status|--install-service|--upgrade-service] [--lan-address PRIVATE_IP --app-url http://PRIVATE_IP:8000 --status-port 8001] [--confirm] [--allow-migration]'; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
    esac
done
[[ "$ROOT_DIR" == /* && -d "$ROOT_DIR" && ! -L "$ROOT_DIR" ]] || { echo 'Existing canonical installation root required.' >&2; exit 1; }
[[ "$(cd -- "$ROOT_DIR" && pwd -P)" == "$ROOT_DIR" ]] || { echo 'Symlinked/noncanonical installation root refused.' >&2; exit 1; }
if [[ "$ACTION" == install ]]; then
    # Explicit privilege boundary: this installer writes systemd units/host files.
    exec bash "$ROOT_DIR/app/deployment/install_updater_service.sh" --root "$ROOT_DIR" "${INSTALL_ARGS[@]}"
fi
PYTHON="$ROOT_DIR/updater/venv/bin/python"
[[ -x "$PYTHON" && -d "$ROOT_DIR/updater/runtime/workout_updater" ]] || {
    echo 'Host updater is not installed. First run --install-service with --lan-address and --app-url; see deployment/README.md.' >&2
    exit 1
}
export PYTHONPATH="$ROOT_DIR/updater/runtime"
# Only fixed subcommands/options can reach the engine; no eval or shell strings.
case "$ACTION" in
    check|status) exec "$PYTHON" -m workout_updater "$ACTION" --root "$ROOT_DIR" ;;
    update) exec "$PYTHON" -m workout_updater update --root "$ROOT_DIR" "${ENGINE_ARGS[@]}" ;;
esac
