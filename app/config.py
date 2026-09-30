import os

AT_PORT = os.getenv("AT_PORT", "/dev/ttyUSB2")
BAUD_RATE = int(os.getenv("BAUD_RATE", "115200"))
TIMEOUT = int(os.getenv("TIMEOUT", "5"))

CONFIG_DIR = os.getenv("CONFIG_DIR", "/var/lib/cellular-config")
CAPTURES_DIR = os.getenv("CAPTURES_DIR", "/var/lib/cellular-captures")
SCRIPTS_DIR = os.getenv("SCRIPTS_DIR", "/opt/scripts")

DB_PATH = os.path.join(CONFIG_DIR, "cellular.db")
AUDIT_DB_PATH = os.path.join(CONFIG_DIR, "audit.db")

CAPTURE_RETENTION_DAYS = int(os.getenv("CAPTURE_RETENTION_DAYS", "7"))
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "15"))

CON_NAME = os.getenv("CON_NAME", "cellular")
DEFAULT_APN = os.getenv("DEFAULT_APN", "pdn-1")
DEFAULT_ROUTE_METRIC = int(os.getenv("DEFAULT_ROUTE_METRIC", "50"))
