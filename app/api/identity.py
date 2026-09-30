import re
import random
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, Optional
from app.utils.at_command import send_at
from app.utils.mmcli_parser import get_imei, get_imsi, get_iccid
from app.utils.audit_log import log_operation



REAL_TACS = [
    "35326005", "35845805", "35316309", "35207606",
    "35299907", "35404207", "86152803", "86891703"
]


def luhn_check_digit(body: str) -> int:
    """Calculate Luhn check digit for 14-digit body using standard Luhn algorithm."""
    total = 0
    for i, d in enumerate(body[::-1]):
        d = int(d)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10


def validate_imei(imei: str) -> bool:
    """Validate 15-digit Luhn IMEI."""
    if not re.match(r"^\d{15}$", imei):
        return False
    return luhn_check_digit(imei[:14]) == int(imei[14])


def generate_random_imei() -> str:
    """Generate a random valid IMEI."""
    tac = random.choice(REAL_TACS)
    serial_num = random.randint(0, 999999)
    serial_str = f"{serial_num:06d}"
    body = f"{tac}{serial_str}"
    return f"{body}{luhn_check_digit(body)}"


def get_identity() -> Dict:
    """Get current IMEI, IMSI, ICCID."""
    return {
        "imei": get_imei(),
        "imsi": get_imsi(),
        "iccid": get_iccid()
    }


def change_imei(new_imei: str, orig_file: str = "/home/one/.imei-original") -> Dict:
    """
    Change modem IMEI.
    
    Args:
        new_imei: 15-digit IMEI to set
        orig_file: Path to store original IMEI
    
    Returns:
        {"success": bool, "message": str}
    """
    if not validate_imei(new_imei):
        return {"success": False, "message": "Invalid IMEI (Luhn check failed)"}
    
    current_imei = get_imei()
    
    if not current_imei:
        return {"success": False, "message": "Cannot read current IMEI"}
    
    orig_path = Path(orig_file)
    if not orig_path.exists():
        try:
            orig_path.write_text(current_imei)
            logging.info(f"Saved original IMEI to {orig_file}")
        except Exception as e:
            logging.warning(f"Failed to save original IMEI: {e}")
    
    try:
        subprocess.run(["systemctl", "stop", "ModemManager"], check=True)
        
        success, resp = send_at(f'AT+EGMR=1,7,"{new_imei}"')
        if not success:
            subprocess.run(["systemctl", "start", "ModemManager"])
            return {"success": False, "message": f"EGMR write failed: {resp}"}
        
        send_at("AT+CFUN=1,1")
        
        time.sleep(45)
        
        subprocess.run(["systemctl", "start", "ModemManager"], check=True)
        
        time.sleep(10)
        
        actual_imei = get_imei()
        
        if actual_imei == new_imei:
            log_operation("IMEI_CHANGE", f"IMEI changed", old_value=current_imei, new_value=new_imei)
            return {"success": True, "message": f"IMEI changed to {new_imei}"}
        else:
            return {"success": False, "message": f"Verification failed: got {actual_imei}"}
    
    except Exception as e:
        logging.error(f"IMEI change failed: {e}")
        return {"success": False, "message": f"Failed: {e}"}


def restore_imei(orig_file: str = "/home/one/.imei-original") -> Dict:
    """
    Restore original IMEI from file.
    
    Args:
        orig_file: Path to stored original IMEI
    
    Returns:
        {"success": bool, "message": str}
    """
    orig_path = Path(orig_file)
    
    if not orig_path.exists():
        return {"success": False, "message": f"No saved original IMEI at {orig_file}"}
    
    try:
        original_imei = orig_path.read_text().strip()
        result = change_imei(original_imei, orig_file)
        
        if result["success"]:
            log_operation("IMEI_RESTORE", "IMEI restored to original", old_value="", new_value=original_imei)
        
        return result
    except Exception as e:
        return {"success": False, "message": f"Failed to read original IMEI: {e}"}
