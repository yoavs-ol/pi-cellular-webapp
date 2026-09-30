import serial
import time
import logging
from typing import Tuple
from app.config import AT_PORT, BAUD_RATE, TIMEOUT

logger = logging.getLogger(__name__)


def send_at_with_retry(command: str, port: str = AT_PORT, timeout: int = TIMEOUT, retries: int = 3) -> Tuple[bool, str]:
    """
    Send AT command with retry logic.
    
    Args:
        command: AT command string
        port: Serial port
        timeout: Timeout in seconds
        retries: Number of retry attempts
    
    Returns:
        Tuple of (success: bool, response: str)
    """
    for attempt in range(retries):
        success, response = send_at(command, port, timeout)
        if success or "Serial error" not in response:
            return success, response
        
        logger.warning(f"AT command failed (attempt {attempt + 1}/{retries}): {response}")
        if attempt < retries - 1:
            time.sleep(1)
    
    return False, f"Failed after {retries} attempts: {response}"


def send_at(command: str, port: str = AT_PORT, timeout: int = TIMEOUT) -> Tuple[bool, str]:
    """
    Send AT command and return (success, response).
    
    Stops ModemManager before calling (race condition prevention).
    
    Args:
        command: AT command string (e.g., "AT+CPIN?")
        port: Serial port (default: /dev/ttyUSB2)
        timeout: Timeout in seconds
    
    Returns:
        Tuple of (success: bool, response: str)
    """
    try:
        with serial.Serial(port, BAUD_RATE, timeout=timeout) as ser:
            ser.reset_input_buffer()
            ser.write((command + "\r").encode())
            
            buf = ""
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                buf += ser.read(4096).decode(errors="replace")
                if "OK" in buf or "ERROR" in buf:
                    break
            
            success = "OK" in buf
            return success, buf.strip()
    except serial.SerialException as e:
        return False, f"Serial error: {e}"


def send_at_wait(command: str, port: str = AT_PORT, wait_time: float = 0.5) -> Tuple[bool, str]:
    """
    Send AT command with additional wait time for slow responses.
    
    Args:
        command: AT command string
        port: Serial port
        wait_time: Additional seconds to wait after sending
    
    Returns:
        Tuple of (success: bool, response: str)
    """
    try:
        with serial.Serial(port, BAUD_RATE, timeout=TIMEOUT) as ser:
            ser.reset_input_buffer()
            ser.write((command + "\r").encode())
            time.sleep(wait_time)
            
            buf = ""
            deadline = time.monotonic() + TIMEOUT
            while time.monotonic() < deadline:
                buf += ser.read(4096).decode(errors="replace")
                if "OK" in buf or "ERROR" in buf:
                    break
            
            success = "OK" in buf
            return success, buf.strip()
    except serial.SerialException as e:
        return False, f"Serial error: {e}"
