import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from app.config import CAPTURES_DIR
from app.utils.audit_log import log_operation

logging.basicConfig(level=logging.INFO)


def start_capture(duration: int = 60, mode: str = "live") -> Dict:
    """
    Start RRC capture.
    
    Args:
        duration: Capture duration in seconds (fixed at 60s per requirements)
        mode: "live" (GSMTAP/SCAT) or "qmdl" (raw Quectel log)
    
    Returns:
        {"success": bool, "filename": str, "message": str}
    """
    if duration != 60:
        duration = 60
    
    Path(CAPTURES_DIR).mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{timestamp}.{mode}"
    filepath = Path(CAPTURES_DIR) / filename
    
    try:
        if mode == "live":
            cmd = f"timeout {duration} signal-cat --serial /dev/ttyUSB0 --gsmtap --output {filepath}"
        else:
            cmd = f"timeout {duration} qlog -d /dev/ttyUSB0 -f {filepath}"
        
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        log_operation("CAPTURE_START", f"Started {duration}s {mode} capture")
        
        return {
            "success": True,
            "filename": filename,
            "message": f"Capture started ({mode}, {duration}s)"
        }
    except Exception as e:
        logging.error(f"Capture failed: {e}")
        return {"success": False, "message": f"Capture failed: {e}"}


def list_captures() -> List[Dict]:
    """
    List available capture files.
    
    Returns:
        List of {"filename": str, "size": int, "mtime": str}
    """
    captures_dir = Path(CAPTURES_DIR)
    
    if not captures_dir.exists():
        return []
    
    captures = []
    for f in captures_dir.glob("*"):
        if f.is_file() and f.suffix in [".pcap", ".qmdl2"]:
            stat = f.stat()
            captures.append({
                "filename": f.name,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(f)
            })
    
    return sorted(captures, key=lambda x: x["mtime"], reverse=True)


def delete_capture(filename: str) -> Dict:
    """
    Delete a capture file.
    
    Args:
        filename: Filename to delete
    
    Returns:
        {"success": bool, "message": str}
    """
    filepath = Path(CAPTURES_DIR) / filename
    
    if not filepath.exists():
        return {"success": False, "message": "File not found"}
    
    try:
        filepath.unlink()
        log_operation("CAPTURE_DELETE", f"Deleted {filename}")
        return {"success": True, "message": f"Deleted {filename}"}
    except Exception as e:
        return {"success": False, "message": f"Delete failed: {e}"}
