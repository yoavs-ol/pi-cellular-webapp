#!/bin/bash
set -euo pipefail

# Cellular Modem Configuration Service - Install Script
# Target: Raspberry Pi with Quectel RM520N-GL 5G HAT
# Usage: bash install.sh

REPO_URL="${REPO_URL:-https://github.com/your-org/pi-cellular-webapp.git}"
INSTALL_DIR="${INSTALL_DIR:-/opt/cellular-config}"
DATA_DIR="${DATA_DIR:-/var/lib/cellular-config}"
CAPTURES_DIR="${CAPTURES_DIR:-/var/lib/cellular-captures}"
SERVICE_USER="${SERVICE_USER:-one}"
SERVICE_GROUP="${SERVICE_GROUP:-one}"

log() { echo "[$(date +%H:%M:%S)] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- Pre-flight checks ---
log "=== Pre-flight checks ==="

[[ $EUID -eq 0 ]] || die "This script must be run as root (use sudo)"

[[ -f /proc/device-tree/model ]] || die "Not a Raspberry Pi"
grep -q "Raspberry Pi" /proc/device-tree/model || die "Not a Raspberry Pi"

[[ -e /dev/ttyUSB2 ]] || die "Modem AT port /dev/ttyUSB2 not found"
[[ -e /dev/cdc-wdm0 ]] || die "Modem QMI port /dev/cdc-wdm0 not found"

log "Hardware detected: $(cat /proc/device-tree/model | tr -d '\0')"

# --- System packages ---
log "=== Installing system packages ==="

apt-get update -qq
apt-get install -y -qq \
    modemmanager \
    libqmi-utils \
    python3 \
    python3-pip \
    python3-venv \
    python3-serial \
    sqlite3 \
    git \
    curl \
    wget \
    > /dev/null

log "System packages installed"

# --- Enable ModemManager ---
log "=== Enabling ModemManager ==="

systemctl enable --now ModemManager
sleep 2

if ! systemctl is-active --quiet ModemManager; then
    die "ModemManager failed to start"
fi

log "ModemManager is running"

# --- Wait for modem detection ---
log "=== Waiting for modem detection ==="

for i in $(seq 1 30); do
    if mmcli -L 2>/dev/null | grep -q Quectel; then
        log "Modem detected by ModemManager"
        break
    fi
    sleep 2
done

mmcli -L 2>/dev/null | grep -q Quectel || die "Modem not detected by ModemManager after 60s"

# --- Create directories ---
log "=== Creating directories ==="

mkdir -p "$INSTALL_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$CAPTURES_DIR"

chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$CAPTURES_DIR"

log "Directories created"

# --- Copy application files ---
log "=== Installing application ==="

# If running from this script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/app/main.py" ]]; then
    log "Copying from $SCRIPT_DIR"
    cp -r "$SCRIPT_DIR/app" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/scripts" "$INSTALL_DIR/"
    cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
else
    log "Cloning from $REPO_URL"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"

log "Application installed to $INSTALL_DIR"

# --- Python virtual environment ---
log "=== Setting up Python environment ==="

cd "$INSTALL_DIR"

sudo -u "$SERVICE_USER" python3 -m venv .venv
sudo -u "$SERVICE_USER" .venv/bin/pip install --quiet --upgrade pip
sudo -u "$SERVICE_USER" .venv/bin/pip install --quiet -r requirements.txt

log "Python packages installed"

# --- systemd service ---
log "=== Creating systemd service ==="

cat > /etc/systemd/system/cellular-config.service <<EOF
[Unit]
Description=Cellular Modem Configuration Service
After=network.target ModemManager.service
Wants=ModemManager.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/.venv/bin/gunicorn -b 0.0.0.0:8080 -w 2 --timeout 120 app.main:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cellular-config

log "systemd service created"

# --- File retention timer ---
log "=== Setting up file retention ==="

cat > /usr/local/bin/cellular-cleanup <<'EOF'
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/cellular-config')
from app.utils.file_retention import run_cleanup
run_cleanup()
EOF
chmod +x /usr/local/bin/cellular-cleanup

cat > /etc/systemd/system/cellular-cleanup.timer <<EOF
[Unit]
Description=Clean old cellular captures and logs

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /etc/systemd/system/cellular-cleanup.service <<EOF
[Unit]
Description=Clean files older than retention period

[Service]
Type=oneshot
ExecStart=/usr/local/bin/cellular-cleanup
User=$SERVICE_USER
Group=$SERVICE_GROUP
EOF

systemctl daemon-reload
systemctl enable --now cellular-cleanup.timer

log "File retention configured (daily at 03:00)"

# --- Start service ---
log "=== Starting service ==="

systemctl start cellular-config
sleep 3

if systemctl is-active --quiet cellular-config; then
    log "Service started successfully"
else
    die "Service failed to start. Check: journalctl -u cellular-config -n 50"
fi

# --- Verify ---
log "=== Verifying installation ==="

PI_IP=$(hostname -I | awk '{print $1}')

for i in $(seq 1 10); do
    if curl -sf "http://localhost:8080/health" > /dev/null 2>&1; then
        log "Health check passed"
        break
    fi
    sleep 1
done

curl -sf "http://localhost:8080/health" > /dev/null 2>&1 || die "Health check failed"

# --- Success ---
log "=== Installation complete ==="
echo ""
echo "Cellular Modem Configuration Service"
echo "===================================="
echo ""
echo "Web UI:      http://$PI_IP:8080"
echo "Health:      http://$PI_IP:8080/health"
echo "API status:  http://$PI_IP:8080/api/status"
echo ""
echo "Service management:"
echo "  Status:    systemctl status cellular-config"
echo "  Logs:      journalctl -u cellular-config -f"
echo "  Restart:   systemctl restart cellular-config"
echo "  Stop:      systemctl stop cellular-config"
echo ""
echo "Directories:"
echo "  App:       $INSTALL_DIR"
echo "  Data:      $DATA_DIR"
echo "  Captures:  $CAPTURES_DIR"
echo ""
echo "Installation completed successfully!"
