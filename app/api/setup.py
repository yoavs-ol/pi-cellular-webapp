import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List
from app.utils.at_command import send_at
from app.config import CAPTURES_DIR, DEFAULT_APN, DEFAULT_ROUTE_METRIC, CON_NAME

logger = logging.getLogger(__name__)


def update_apn_metric(apn: str = DEFAULT_APN, metric: int = DEFAULT_ROUTE_METRIC) -> Dict:
    """Quick APN/metric update without full QMI setup."""
    try:
        subprocess.run([
            "sudo", "nmcli", "connection", "modify", CON_NAME,
            "gsm.apn", apn,
            "ipv4.route-metric", str(metric)
        ], check=True, capture_output=True)
        
        subprocess.run(["sudo", "nmcli", "connection", "down", CON_NAME], check=True, capture_output=True)
        time.sleep(2)
        subprocess.run(["sudo", "nmcli", "connection", "up", CON_NAME], check=True, capture_output=True)
        
        from app.utils.audit_log import log_operation
        log_operation("APN_UPDATE", f"Updated APN to {apn}, metric to {metric}")
        
        return {"success": True, "message": f"APN changed to {apn}, metric to {metric}"}
    except subprocess.CalledProcessError as e:
        return {"success": False, "message": f"Update failed: {e}"}


def configure_qmi(apn: str = DEFAULT_APN, metric: int = DEFAULT_ROUTE_METRIC) -> Dict:
    """
    One-shot QMI setup.
    
    Args:
        apn: APN name
        metric: Route metric
    
    Returns:
        {"success": bool, "ip": str, "message": str}
    """
    try:
        lsusb_result = subprocess.run(["lsusb"], capture_output=True, text=True)
        if "2c7c" not in lsusb_result.stdout:
            return {"success": False, "message": "Quectel module not on USB"}
        
        subprocess.run(
            ["sudo", "apt-get", "install", "-y", "modemmanager", "libqmi-utils", "python3-serial"],
            check=True, capture_output=True
        )
        
        subprocess.run(["sudo", "systemctl", "stop", "ModemManager"], check=True)
        
        from app.utils.at_command import send_at
        success, resp = send_at("AT+CPIN?")
        
        if "READY" not in resp:
            subprocess.run(["systemctl", "start", "ModemManager"])
            return {"success": False, "message": f"SIM not ready: {resp}"}
        
        success, resp = send_at('AT+QCFG="usbnet"')
        if '"usbnet",0' not in resp:
            send_at('AT+QCFG="usbnet",0')
            send_at('AT+CFUN=1,1')
            time.sleep(45)
        
        subprocess.run(["sudo", "systemctl", "start", "ModemManager"], check=True)
        time.sleep(10)
        
        for _ in range(30):
            result = subprocess.run(["mmcli", "-L"], capture_output=True, text=True)
            if "Quectel" in result.stdout:
                break
            time.sleep(2)
        
        for _ in range(30):
            result = subprocess.run(["mmcli", "-m", "any"], capture_output=True, text=True)
            if "registered" in result.stdout or "connected" in result.stdout:
                break
            time.sleep(2)
        
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show"],
            capture_output=True, text=True
        )
        
        if CON_NAME in result.stdout:
            subprocess.run([
                "sudo", "nmcli", "connection", "modify", CON_NAME,
                "gsm.apn", apn,
                "ipv6.method", "disabled",
                "ipv4.route-metric", str(metric),
                "connection.autoconnect", "yes"
            ], check=True)
        else:
            subprocess.run([
                "sudo", "nmcli", "connection", "add", "type", "gsm",
                "ifname", "*", "con-name", CON_NAME,
                "gsm.apn", apn,
                "ipv6.method", "disabled",
                "ipv4.route-metric", str(metric),
                "connection.autoconnect", "yes"
            ], check=True)
        
        subprocess.run(["sudo", "nmcli", "connection", "up", CON_NAME], check=True)
        
        time.sleep(3)
        
        ip_result = subprocess.run(
            ["ip", "-br", "addr", "show", "wwan0"],
            capture_output=True, text=True
        )
        
        import re
        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", ip_result.stdout)
        ip = ip_match.group(1) if ip_match else "unknown"
        
        from app.utils.audit_log import log_operation
        log_operation("QMI_SETUP", f"Configured QMI (APN={apn}, metric={metric})")
        
        return {"success": True, "ip": ip, "message": f"QMI configured successfully (IP: {ip})"}
    
    except subprocess.CalledProcessError as e:
        logging.error(f"QMI setup failed: {e}")
        return {"success": False, "message": f"Setup failed: {e}"}
