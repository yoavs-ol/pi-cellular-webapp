# Cellular Modem Configuration Service - Installation Guide

## Overview

This guide provides step-by-step instructions for installing the Cellular Modem Configuration Service on a Raspberry Pi with Waveshare RM520N-GL 5G HAT.

**What this service provides:**
- Web UI for modem configuration (http://<pi-ip>:8080)
- REST API for programmatic access
- IMEI change/restore with validation
- Power control (on/off/reset/shutdown)
- RRC signaling capture
- Operation audit logging
- Network time sync from cellular NITZ

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Hardware Setup](#hardware-setup)
3. [Software Installation](#software-installation)
4. [Service Deployment](#service-deployment)
5. [Verification](#verification)
6. [Post-Installation](#post-installation)
7. [Troubleshooting](#troubleshooting)
8. [Uninstallation](#uninstallation)

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Raspberry Pi | Pi 4 (2GB) | Pi 5 (4GB+) |
| OS | Debian 12 (bookworm) | Debian 13 (trixie) |
| Disk Space | 1GB free | 5GB free |
| RAM | 512MB available | 2GB available |

### Software Requirements

- **Operating System:** Debian 12+ or Raspberry Pi OS (64-bit)
- **Python:** 3.11+
- **Modem:** Quectel RM520N-GL 5G HAT (or compatible Quectel module)
- **Network:** Cellular connection established

### Network Requirements

- SSH access to Raspberry Pi
- Internet connection (for package installation)
- Cellular modem connected via USB

---

## Hardware Setup

### 1. Physical Connections

**Waveshare RM520N-GL 5G HAT:**

1. **Mount HAT on Pi** (GPIO header)
2. **Connect antennas** (4x antenna cables):
   - MAIN: Primary cellular antenna
   - AUX: Diversity antenna
   - GNSS: GPS antenna (optional)
   - DIV: Additional diversity

3. **Insert SIM card** (Slot 1 or 2)

4. **Connect external power** ⚠️ **CRITICAL**
   - Connect 5V/3A power supply to EXT PWR port
   - Set DIP switch to "EXT PWR"
   - **USB-only power will cause brownouts during network attach**

5. **Connect USB cable** (USB 3.0 port on Pi)

### 2. Verify Hardware Detection

```bash
# Check USB enumeration
lsusb | grep Quectel
# Expected output: ID 2c7c:xxxx Quectel Wireless Solutions Co., Ltd.

# Check serial ports
ls /dev/ttyUSB*
# Expected: /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyUSB2 /dev/ttyUSB3

# Check device permissions
groups
# Should include: dialout
```

**Troubleshooting:**
- If no USB devices detected: Check USB cable, external power, and DIP switch
- If permission denied: Add user to `dialout` group: `sudo usermod -aG dialout $USER`

---

## Software Installation

### Step 1: Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### Step 2: Install Dependencies

```bash
# ModemManager and network tools
sudo apt-get install -y \
    modemmanager \
    libqmi-utils \
    python3-serial \
    python3-venv \
    python3-pip \
    sqlite3 \
    iproute2 \
    iputils-ping \
    curl \
    procps
```

### Step 3: Verify ModemManager Detection

```bash
# Check ModemManager sees the modem
mmcli -L

# Expected output:
# /org/freedesktop/ModemManager1/Modem/0 [Quectel] RM520N-GL

# Check modem status
mmcli -m any

# Check SIM
mmcli -m any -K | grep sim
```

**If modem not detected:**
```bash
# Restart ModemManager
sudo systemctl restart ModemManager

# Wait 10 seconds
sleep 10

# Check again
mmcli -L
```

### Step 4: Establish Cellular Connection

**Option A: Using existing scripts (if available)**

```bash
# If you have setup-qmi-cellular.sh
bash setup-qmi-cellular.sh
```

**Option B: Manual QMI setup**

```bash
# Stop ModemManager for AT access
sudo systemctl stop ModemManager

# Send AT commands (as root)
sudo -s

# Test AT response
echo -e 'AT\r' > /dev/ttyUSB2
cat /dev/ttyUSB2
# Expected: OK

# Check SIM
echo -e 'AT+CPIN?\r' > /dev/ttyUSB2
cat /dev/ttyUSB2
# Expected: +CPIN: READY

# Set QMI mode (if not already)
echo -e 'AT+QCFG="usbnet"\r' > /dev/ttyUSB2
cat /dev/ttyUSB2
# If response shows not 0, set it:
echo -e 'AT+QCFG="usbnet",0\r' > /dev/ttyUSB2
echo -e 'AT+CFUN=1,1\r' > /dev/ttyUSB2

exit

# Wait for module reboot (45 seconds)
sleep 45

# Start ModemManager
sudo systemctl start ModemManager

# Wait for detection
sleep 10

# Create NetworkManager connection
sudo nmcli connection add type gsm ifname "*" con-name cellular \
    gsm.apn "pdn-1" ipv6.method disabled \
    ipv4.route-metric 50 connection.autoconnect yes

# Activate connection
sudo nmcli connection up cellular

# Verify connection
ip addr show wwan0
ping -I wwan0 -c 3 8.8.8.8
```

---

## Service Deployment

### Method 1: Direct Deployment (Recommended)

**Fastest method - uses systemd service directly**

#### 1. Download Application

```bash
# Create directory
mkdir -p ~/cellular-app
cd ~/cellular-app

# Option A: Clone from repository (if available)
# git clone <repo-url> .

# Option B: Download tarball from development machine
# On your Mac/PC:
# tar czf cellular-app.tar.gz -C pi-cellular-webapp .
# scp cellular-app.tar.gz one@<pi-ip>:/home/one/
# 
# On Pi:
# tar xzf cellular-app.tar.gz -C ~/cellular-app
```

#### 2. Create Python Virtual Environment

```bash
cd ~/cellular-app

# Create venv
python3 -m venv .venv

# Install dependencies
.venv/bin/pip install --no-cache-dir flask pyserial gunicorn
```

#### 3. Prepare Data Directories

```bash
# Create data directories
sudo mkdir -p /var/lib/cellular-config
sudo mkdir -p /var/lib/cellular-captures

# Set ownership
sudo chown $USER:$USER /var/lib/cellular-config
sudo chown $USER:$USER /var/lib/cellular-captures

# Verify
ls -la /var/lib/ | grep cellular
```

#### 4. Install systemd Service

```bash
# Create service file
cat > /tmp/cellular-config.service << 'EOF'
[Unit]
Description=Cellular Modem Configuration Service
After=network.target ModemManager.service

[Service]
Type=simple
User=<USERNAME>
Group=<USERNAME>
WorkingDirectory=/home/<USERNAME>/cellular-app
Environment="PATH=/home/<USERNAME>/cellular-app/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/<USERNAME>/cellular-app/.venv/bin/gunicorn -b 0.0.0.0:8080 -w 2 --timeout 120 app.main:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Replace <USERNAME> with your username
sed -i "s/<USERNAME>/$USER/g" /tmp/cellular-config.service

# Install service
sudo cp /tmp/cellular-config.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cellular-config
sudo systemctl start cellular-config
```

#### 5. Check Service Status

```bash
# Check status
systemctl status cellular-config

# View logs
journalctl -u cellular-config -f
```

### Method 2: Kubernetes Deployment (Advanced)

**For production environments requiring orchestration**

#### 1. Install k3s

```bash
# Install k3s (lightweight Kubernetes)
curl -sfL https://get.k3s.io | sudo sh -

# Wait for k3s to start (2-3 minutes)
sudo systemctl status k3s

# Configure kubectl
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Verify
kubectl get nodes
```

#### 2. Install Container Builder

```bash
# Install buildah
sudo apt-get install -y buildah

# Verify
buildah --version
```

#### 3. Build Container Image

```bash
# Copy application to Pi
# On your Mac:
# tar czf cellular-app.tar.gz -C pi-cellular-webapp .
# scp cellular-app.tar.gz one@<pi-ip>:/tmp/

# On Pi:
cd /tmp
tar xzf cellular-app.tar.gz -C /tmp/cellular-config

# Build image
sudo buildah bud -t cellular-config:latest /tmp/cellular-config

# Push to local registry
sudo buildah push cellular-config:latest docker-daemon:cellular-config:latest
```

#### 4. Deploy to k3s

```bash
# Apply Kubernetes manifests
kubectl apply -f /tmp/cellular-config/k8s/deployment.yaml
kubectl apply -f /tmp/cellular-config/k8s/service.yaml
kubectl apply -f /tmp/cellular-config/k8s/cleanup-cronjob.yaml

# Verify deployment
kubectl get pods
kubectl logs -f deployment/cellular-config
```

**Resource usage comparison:**

| Method | Memory | Disk | Startup Time |
|--------|--------|------|--------------|
| Direct (systemd) | ~100MB | ~50MB | ~2s |
| k3s (container) | ~500MB | ~500MB | ~30s |

---

## Verification

### 1. Service Health Check

```bash
# HTTP health endpoint
curl http://localhost:8080/health
# Expected: OK

# Modem status API
curl http://localhost:8080/api/status | python3 -m json.tool
# Expected: JSON with IMEI, IMSI, signal, etc.
```

### 2. Web UI Access

Open browser: `http://<pi-ip>:8080`

**Expected features:**
- Dashboard with real-time status
- Setup page (if modem not configured)
- Identity page (IMEI viewer)
- Power control
- Signaling capture
- Operation logs
- Troubleshooting guide

### 3. API Testing

```bash
# Identity
curl http://localhost:8080/api/identity

# Network time
curl http://localhost:8080/api/time

# Power status
curl -X POST http://localhost:8080/api/power/off  # Turn radio off
curl -X POST http://localhost:8080/api/power/on   # Turn radio on
```

### 4. Systemd Service Verification

```bash
# Check enabled
systemctl is-enabled cellular-config
# Expected: enabled

# Check running
systemctl is-active cellular-config
# Expected: active

# Check logs
journalctl -u cellular-config --no-pager -n 50
```

---

## Post-Installation

### 1. Configure File Retention (Optional)

**Automatic cleanup via systemd timer:**

```bash
# Create systemd timer
cat > /tmp/cellular-cleanup.timer << 'EOF'
[Unit]
Description=Clean old cellular captures and logs daily

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

cat > /tmp/cellular-cleanup.service << 'EOF'
[Unit]
Description=Clean files older than retention period

[Service]
Type=oneshot
ExecStart=/home/<USERNAME>/cellular-app/.venv/bin/python /home/<USERNAME>/cellular-app/scripts/cleanup.py
User=<USERNAME>
EOF

# Replace <USERNAME>
sed -i "s/<USERNAME>/$USER/g" /tmp/cellular-cleanup.service

# Install
sudo cp /tmp/cellular-cleanup.{timer,service} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cellular-cleanup.timer

# Verify
systemctl list-timers | grep cellular
```

### 2. Network Time Sync

The service automatically syncs from cellular NITZ on startup.

**Manual sync:**
```bash
curl -X POST http://localhost:8080/api/time/sync
```

### 3. Security Considerations

**Current security posture:**
- ✅ Runs as non-root user
- ✅ Uses sudo only for modem operations
- ⚠️ No authentication (LAN only)
- ⚠️ No TLS (HTTP only)

**For production:**
1. **Add reverse proxy with TLS:**
   ```bash
   sudo apt-get install -y nginx
   ```

2. **Configure firewall:**
   ```bash
   sudo apt-get install -y ufw
   sudo ufw allow from 192.168.60.0/24 to any port 8080
   sudo ufw enable
   ```

3. **Add basic auth** (modify `app/main.py`)

### 4. Backup Configuration

```bash
# Backup application
tar czf cellular-app-backup-$(date +%Y%m%d).tar.gz -C ~/ cellular-app

# Backup data directories
sudo tar czf cellular-data-backup-$(date +%Y%m%d).tar.gz \
    -C /var/lib cellular-config cellular-captures

# Store backups securely
```

---

## Troubleshooting

### Service Won't Start

**Symptoms:**
- `systemctl status cellular-config` shows failed
- Web UI not accessible

**Diagnostic steps:**

```bash
# Check logs
journalctl -u cellular-config -xe

# Check Python syntax
cd ~/cellular-app
.venv/bin/python -m py_compile app/main.py

# Check port availability
sudo netstat -tlnp | grep 8080

# Check ModemManager
systemctl status ModemManager
```

**Common fixes:**

1. **Permission denied:**
   ```bash
   sudo usermod -aG dialout $USER
   # Logout and login again
   ```

2. **Port already in use:**
   ```bash
   sudo lsof -i :8080
   sudo kill <pid>
   ```

3. **ModemManager not running:**
   ```bash
   sudo systemctl restart ModemManager
   ```

### Modem Not Detected

**Symptoms:**
- `mmcli -L` shows no modems
- `/api/status` returns empty data

**Diagnostic steps:**

```bash
# Check USB
lsusb | grep Quectel

# Check serial ports
ls -la /dev/ttyUSB*

# Check ModemManager logs
journalctl -u ModemManager -f
```

**Fixes:**

1. **USB not detected:**
   - Check USB cable connection
   - Check external power (5V/3A)
   - Try different USB port

2. **Serial ports not accessible:**
   ```bash
   sudo usermod -aG dialout $USER
   # Reboot
   ```

3. **ModemManager not detecting:**
   ```bash
   # Force detection
   sudo udevadm trigger
   
   # Restart MM
   sudo systemctl restart ModemManager
   ```

### No Network Connection

**Symptoms:**
- `ip addr show wwan0` shows no IP
- No internet via cellular

**Diagnostic steps:**

```bash
# Check registration
mmcli -m any | grep -i stat

# Check connection
nmcli connection show

# Test AT commands
sudo systemctl stop ModemManager
echo -e 'AT+CEREG?\r' | sudo tee /dev/ttyUSB2
cat /dev/ttyUSB2
sudo systemctl start ModemManager
```

**Fixes:**

1. **Not registered:**
   ```bash
   # Check signal
   mmcli -m any | grep signal
   
   # Check SIM
   mmcli -m any -K | grep sim
   ```

2. **Connection down:**
   ```bash
   sudo nmcli connection up cellular
   ```

### Slow Performance

**Symptoms:**
- UI takes long to load
- API timeouts

**Diagnostic steps:**

```bash
# Check CPU
top

# Check memory
free -h

# Check disk
df -h

# Check service resource usage
systemctl show cellular-config --property=MemoryCurrent,CPUUsageNSec
```

**Fixes:**

1. **High CPU:**
   - Reduce gunicorn workers: `--workers 1` in service file
   - Disable unused features

2. **High memory:**
   - Set memory limit in service file: `MemoryLimit=256M`

3. **Disk full:**
   ```bash
   # Cleanup old captures
   .venv/bin/python scripts/cleanup.py
   ```

---

## Uninstallation

### Remove Service

```bash
# Stop and disable service
sudo systemctl stop cellular-config
sudo systemctl disable cellular-config

# Remove service file
sudo rm /etc/systemd/system/cellular-config.service
sudo systemctl daemon-reload
```

### Remove Application

```bash
# Remove application
rm -rf ~/cellular-app

# Remove data directories (optional)
sudo rm -rf /var/lib/cellular-config
sudo rm -rf /var/lib/cellular-captures
```

### Remove Dependencies (Optional)

```bash
# Only if no other services need them
sudo apt-get remove -y \
    modemmanager \
    libqmi-utils \
    python3-serial

# Remove Python packages (if no other apps need)
rm -rf ~/cellular-app/.venv
```

### Remove k3s (if installed)

```bash
# Uninstall k3s
sudo /usr/local/bin/k3s-uninstall.sh

# Remove k3s data
sudo rm -rf /var/lib/rancher
```

---

## Appendix A: Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AT_PORT` | `/dev/ttyUSB2` | Modem AT command port |
| `BAUD_RATE` | `115200` | Serial baud rate |
| `CONFIG_DIR` | `/var/lib/cellular-config` | Config data directory |
| `CAPTURES_DIR` | `/var/lib/cellular-captures` | Capture files directory |
| `CAPTURE_RETENTION_DAYS` | `7` | Days to keep captures |
| `LOG_RETENTION_DAYS` | `15` | Days to keep logs |
| `CON_NAME` | `cellular` | NetworkManager connection name |
| `DEFAULT_APN` | `pdn-1` | Default APN name |
| `DEFAULT_ROUTE_METRIC` | `50` | Route metric |

**Usage:**
Add to systemd service file:
```ini
[Service]
Environment="AT_PORT=/dev/ttyUSB2"
Environment="DEFAULT_APN=internet"
```

### Service File Options

```ini
[Service]
# Resource limits
MemoryLimit=512M
CPUQuota=50%

# Restart policy
Restart=on-failure
RestartSec=30
StartLimitIntervalSec=300
StartLimitBurst=5

# Security
NoNewPrivileges=true
PrivateTmp=true
```

---

## Appendix B: API Reference

### Endpoints

| Method | Endpoint | Description | Example |
|--------|----------|-------------|----------|
| GET | `/` | Dashboard UI | - |
| GET | `/setup` | Setup UI | - |
| POST | `/setup` | Configure QMI | `apn=pdn-1&metric=50` |
| GET | `/identity` | Identity UI | - |
| GET | `/api/identity` | Get IMEI/IMSI/ICCID | - |
| POST | `/api/identity/change` | Change IMEI | `action=random` or `action=set&imei=...` |
| GET | `/power` | Power UI | - |
| POST | `/api/power/on` | Turn radio on | - |
| POST | `/api/power/off` | Turn radio off | - |
| POST | `/api/power/reset` | Reboot module | - |
| POST | `/api/power/shutdown` | Full power down | `force=true` |
| GET | `/signaling` | Signaling UI | - |
| POST | `/api/capture/start` | Start capture | `duration=60&mode=live` |
| GET | `/api/captures` | List captures | - |
| DELETE | `/api/captures/<file>` | Delete capture | - |
| GET | `/downloads/<file>` | Download capture | - |
| GET | `/logs` | Logs UI | - |
| GET | `/api/logs` | Get audit log | `?limit=100` |
| GET | `/api/status` | Modem status | - |
| GET | `/api/time` | Network time | - |
| POST | `/api/time/sync` | Sync system clock | `allow_backward=false` |
| POST | `/api/cleanup` | Run file cleanup | - |
| GET | `/health` | Health check | - |

### Response Examples

**GET `/api/status`:**
```json
{
  "imei": "868371055978783",
  "imsi": "999400000556409",
  "iccid": "8900099200002064096",
  "operator": "999 40",
  "signal": 81,
  "rat": "5G-SA",
  "state": "connected",
  "ip": "192.168.130.94"
}
```

**POST `/api/identity/change` response:**
```json
{
  "success": true,
  "message": "IMEI changed to 353260051234567"
}
```

---

## Appendix C: File Locations

### Application Files

| Location | Purpose |
|----------|---------|
| `/home/<user>/cellular-app/` | Application root |
| `/home/<user>/cellular-app/app/` | Python modules |
| `/home/<user>/cellular-app/.venv/` | Virtual environment |
| `/home/<user>/cellular-app/scripts/` | Utility scripts |

### Data Files

| Location | Purpose |
|----------|---------|
| `/var/lib/cellular-config/` | Configuration data |
| `/var/lib/cellular-config/cellular.db` | SQLite database |
| `/var/lib/cellular-config/audit.db` | Audit log database |
| `/var/lib/cellular-captures/` | RRC capture files |

### System Files

| Location | Purpose |
|----------|---------|
| `/etc/systemd/system/cellular-config.service` | Service unit |
| `/etc/systemd/system/cellular-cleanup.timer` | Cleanup timer |
| `/var/log/journal/` | System logs |

---

## Appendix D: Hardware Specifications

### Waveshare RM520N-GL 5G HAT

| Specification | Value |
|--------------|-------|
| Module | Quectel RM520N-GL |
| Platform | Qualcomm X62 |
| 3GPP Release | 16 |
| 5G Bands | n1–n79 (Sub-6 GHz) |
| LTE Bands | B1–B66 |
| Peak Speed (SA) | DL 2.4 Gbps / UL 900 Mbps |
| Peak Speed (NSA) | DL 3.4 Gbps |
| Peak Speed (LTE) | DL 1.6 Gbps |
| Interfaces | USB 3.x, SIM (2x), GNSS |
| Power | 5V/3A external required |
| Form Factor | Raspberry Pi HAT |

### Serial Port Mapping

| Device | Purpose |
|--------|---------|
| `/dev/ttyUSB0` | DIAG (debug/QXDM) |
| `/dev/ttyUSB1` | NMEA (GNSS output) |
| `/dev/ttyUSB2` | AT command port ⭐ |
| `/dev/ttyUSB3` | Modem data |

### Power Requirements

| Mode | Current | Notes |
|------|---------|-------|
| Idle | ~200mA | USB powered OK |
| Connected | ~500mA | USB powered marginal |
| Active data | ~1.5A | ⚠️ External power required |
| Peak (attach) | ~2.5A | ⚠️ External power required |

**Warning:** USB-only power will cause brownouts and reboots during network attachment.

---

## Appendix E: Useful Commands

### Service Management

```bash
# Start
sudo systemctl start cellular-config

# Stop
sudo systemctl stop cellular-config

# Restart
sudo systemctl restart cellular-config

# Status
systemctl status cellular-config

# Logs
journalctl -u cellular-config -f

# Enable on boot
sudo systemctl enable cellular-config

# Disable on boot
sudo systemctl disable cellular-config
```

### Modem Management

```bash
# List modems
mmcli -L

# Get modem info
mmcli -m any

# Get SIM info
mmcli -m any -K | grep sim

# Enable modem
sudo mmcli -m any --enable

# Disable modem
sudo mmcli -m any --disable

# Reset modem
sudo mmcli -m any --reset
```

### AT Commands (via serial)

```bash
# Interactive
sudo minicom -D /dev/ttyUSB2

# Scripted (as root)
sudo -s
echo -e 'AT\r' > /dev/ttyUSB2
cat /dev/ttyUSB2
echo -e 'AT+CPIN?\r' > /dev/ttyUSB2
cat /dev/ttyUSB2
echo -e 'AT+QENG="servingcell"\r' > /dev/ttyUSB2
cat /dev/ttyUSB2
exit
```

### Network Management

```bash
# List connections
nmcli connection show

# Connection status
nmcli connection show cellular

# Activate connection
sudo nmcli connection up cellular

# Deactivate connection
sudo nmcli connection down cellular

# Check interface
ip addr show wwan0

# Test connectivity
ping -I wwan0 -c 3 8.8.8.8
```

---

## Appendix F: Changelog

### Version 1.0.0 (2026-09-30)

**Features:**
- Initial release
- Dashboard with real-time status
- QMI setup automation
- IMEI change/restore with validation
- Power control (on/off/reset/shutdown)
- RRC capture (60s fixed)
- Operation audit logging
- Network time sync from NITZ
- Web UI with Bootstrap 5
- REST API for all operations
- Systemd service deployment
- Kubernetes manifests (optional)

**Known Limitations:**
- No authentication
- No TLS
- Fixed 60s capture duration
- Requires privileged container for clock sync

---

## Support

**Documentation:**
- Project README: `pi-cellular-webapp/README.md`
- Deployment status: `pi-cellular-webapp/DEPLOYMENT_STATUS.md`
- Hardware reference: `pi-cellular-tool/CLAUDE.md`

**Troubleshooting:**
- Web UI: http://<pi-ip>:8080/troubleshooting
- Logs: `journalctl -u cellular-config -f`

**Hardware Manual:**
https://files.waveshare.com/upload/8/8a/Quectel_RG520N%26RG52xF%26RG530F%26RM520N%26RM530N_Series_AT_Commands_Manual_V1.0.0_Preliminary_20220812.pdf

---

**Installation Guide Version:** 1.0.0  
**Last Updated:** 2026-09-30  
**Authors:** OpenCode Agent
