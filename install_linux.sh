#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${HOME}/.local/bin"
ICON_ROOT="${DATA_HOME}/icons/hicolor"
APPLICATIONS_DIR="${DATA_HOME}/applications"
DESKTOP_FILE="${APPLICATIONS_DIR}/atof.desktop"
APP_LAUNCHER="${BIN_HOME}/atof"

if [[ -n "${ATOF_PYTHON:-}" ]]; then
    candidates=("$ATOF_PYTHON")
else
    candidates=(
        "${APP_DIR}/.venv/bin/python"
        "${APP_DIR}/.venv/bin/python3"
        "$(command -v python3 || true)"
        "$(command -v python || true)"
    )
fi

PYTHON_BIN=""
for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]] && "$candidate" -c 'import pygame' >/dev/null 2>&1; then
        PYTHON_BIN="$(realpath "$candidate")"
        break
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    printf '%s\n' "Could not find a Python interpreter with pygame installed." >&2
    printf '%s\n' "Install pygame in your Python environment, then rerun with ATOF_PYTHON=/path/to/python." >&2
    exit 1
fi

mkdir -p "$BIN_HOME" "$APPLICATIONS_DIR"

printf -v APP_DIR_Q '%q' "$APP_DIR"
printf -v PYTHON_BIN_Q '%q' "$PYTHON_BIN"
cat > "$APP_LAUNCHER" <<EOF
#!/usr/bin/env bash
cd -- ${APP_DIR_Q}
export SDL_VIDEO_X11_WMCLASS=atof
export SDL_VIDEO_WAYLAND_WMCLASS=atof
exec ${PYTHON_BIN_Q} ${APP_DIR_Q}/main.py "\$@"
EOF
chmod 755 "$APP_LAUNCHER"

desktop_quote() {
    local value="$1"
    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    value="${value//\$/\\$}"
    value="${value//\`/\\\`}"
    printf '"%s"' "$value"
}

printf -v EXEC_Q '%s' "$(desktop_quote "$APP_LAUNCHER")"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=ATOF
Comment=Game About Mister Atom
Exec=${EXEC_Q}
Icon=atof
Terminal=false
Categories=Game;
StartupNotify=true
StartupWMClass=atof
EOF
chmod 644 "$DESKTOP_FILE"

for size in 16 24 32 48 64 128 256; do
    icon="${APP_DIR}/icon_${size}.png"
    if [[ -f "$icon" ]]; then
        icon_dir="${ICON_ROOT}/${size}x${size}/apps"
        mkdir -p "$icon_dir"
        install -m 644 "$icon" "${icon_dir}/atof.png"
    fi
done

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache --force "$ICON_ROOT" >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$DESKTOP_FILE"
fi

if command -v gsettings >/dev/null 2>&1 &&
    gsettings list-schemas | grep -qx 'org.gnome.shell'; then
    favorites="$(gsettings get org.gnome.shell favorite-apps)"
    if [[ "$favorites" != *"'atof.desktop'"* ]]; then
        gsettings set org.gnome.shell favorite-apps "${favorites%]}, 'atof.desktop']"
    fi
fi

printf 'Installed ATOF desktop integration:\n  %s\n  %s\n' "$DESKTOP_FILE" "$APP_LAUNCHER"
