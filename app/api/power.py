import subprocess
import time
import logging
from typing import Dict
from app.config import CON_NAME
from app.utils.audit_log import log_operation

logging.basicConfig(level=logging.INFO)


def get_power_status() -> Dict:
    """Get current power/radio status."""
    try:
        result = subprocess.run(
            ["mmcli", "-m", "any"],
            capture_output=True, text=True, timeout=5
        )
        
        state = "unknown"
        power_state = "unknown"
        
        for line in result.stdout.splitlines():
            if "state:" in line.lower():
                state = line.split(":", 1)[1].strip()
            elif "power state:" in line.lower():
                power_state = line.split(":", 1)[1].strip()
        
        return {
            "state": state,
            "power_state": power_state
        }
    except Exception as e:
        logging.error(f"Failed to get power status: {e}")
        return {"error": str(e)}


def radio_off() -> Dict:
    """
    Turn radio off (airplane mode).
    
    Returns:
        {"success": bool, "message": str}
    """
    try:
        subprocess.run(["nmcli", "connection", "modify", CON_NAME, "connection.autoconnect", "no"], check=True)
        subprocess.run(["mmcli", "-m", "any", "--disable"], check=True)
        
        log_operation("RADIO_OFF", "Radio disabled (airplane mode)")
        
        return {"success": True, "message": "Radio turned off"}
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to turn radio off: {e}")
        return {"success": False, "message": f"Failed: {e.stderr}"}


def radio_on() -> Dict:
    """
    Turn radio on and reactivate connection.
    
    Returns:
        {"success": bool, "message": str}
    """
    try:
        subprocess.run(["nmcli", "connection", "modify", CON_NAME, "connection.autoconnect", "yes"], check=True)
        subprocess.run(["mmcli", "-m", "any", "--enable"], check=True)
        
        time.sleep(5)
        
        for _ in range(30):
            result = subprocess.run(
                ["mmcli", "-m", "any"],
                capture_output=True, text=True
            )
            if "registered" in result.stdout or "connected" in result.stdout:
                break
            time.sleep(2)
        
        subprocess.run(["nmcli", "connection", "up", CON_NAME], check=True)
        
        log_operation("RADIO_ON", "Radio enabled and connection activated")
        
        return {"success": True, "message": "Radio turned on and connection activated"}
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to turn radio on: {e}")
        return {"success": False, "message": f"Failed: {e}"}


def reset_modem() -> Dict:
    """
    Reset modem module (full reboot, ~45s).
    
    Returns:
        {"success": bool, "message": str}
    """
    try:
        log_operation("MODEM_RESET", "Module reboot initiated")
        
        subprocess.run(["mmcli", "-m", "any", "--reset"], check=True)
        
        time.sleep(10)
        
        for _ in range(40):
            result = subprocess.run(
                ["mmcli", "-L"],
                capture_output=True, text=True
            )
            if "Quectel" in result.stdout:
                break
            time.sleep(2)
        
        log_operation("MODEM_RESET", "Module reboot complete")
        
        return {"success": True, "message": "Modem reset complete (~45s)"}
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to reset modem: {e}")
        return {"success": False, "message": f"Failed: {e}"}


def shutdown_modem(force: bool = False) -> Dict:
    """
    Full modem power-down (requires physical power cycle to restore).
    
    Args:
        force: Skip confirmation warning
    
    Returns:
        {"success": bool, "message": str}
    """
    try:
        if not force:
            return {"success": False, "message": "Requires force=True or confirmation"}
        
        log_operation("MODEM_SHUTDOWN", "Module powered down (requires physical power cycle)")
        
        subprocess.run(["systemctl", "stop", "ModemManager"], check=True)
        
        from app.utils.at_command import send_at
        send_at("AT+QPOWD=1")
        
        return {"success": True, "message": "Modem powered down. Power-cycle HAT to restore."}
    except Exception as e:
        logging.error(f"Failed to shutdown modem: {e}")
        return {"success": False, "message": f"Failed: {e}"}
