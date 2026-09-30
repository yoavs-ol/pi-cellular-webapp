from pathlib import Path
from datetime import datetime, timedelta
import logging
from app.config import CAPTURES_DIR, CONFIG_DIR, CAPTURE_RETENTION_DAYS, LOG_RETENTION_DAYS

logging.basicConfig(level=logging.INFO)


def clean_old_files(directory: Path, days: int) -> int:
    """
    Delete files older than specified days.
    
    Args:
        directory: Directory to clean
        days: Age threshold in days
    
    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0
    
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    
    for f in directory.glob("*"):
        if f.is_file():
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    logging.info(f"Deleting {f} (mtime={mtime})")
                    f.unlink()
                    count += 1
            except Exception as e:
                logging.warning(f"Failed to delete {f}: {e}")
    
    return count


def run_cleanup():
    """Run cleanup for captures and logs."""
    captures_path = Path(CAPTURES_DIR)
    logs_path = Path(CONFIG_DIR)
    
    captures_cleaned = clean_old_files(captures_path, CAPTURE_RETENTION_DAYS)
    logs_cleaned = clean_old_files(logs_path, LOG_RETENTION_DAYS)
    
    logging.info(f"Cleanup complete: {captures_cleaned} captures, {logs_cleaned} logs deleted")
    
    return {
        "captures_deleted": captures_cleaned,
        "logs_deleted": logs_cleaned,
        "captures_retention_days": CAPTURE_RETENTION_DAYS,
        "logs_retention_days": LOG_RETENTION_DAYS
    }


if __name__ == "__main__":
    run_cleanup()
