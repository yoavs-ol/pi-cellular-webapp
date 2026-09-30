# Cellular Modem Configuration Service - Test Plan

## Test Objectives

1. Verify all API endpoints return correct responses
2. Validate error handling and edge cases
3. Test integration with ModemManager and serial ports
4. Verify UI functionality and accessibility
5. Test security vulnerabilities
6. Validate data persistence and file operations

---

## Test Categories

### 1. Unit Tests

#### 1.1 AT Command Module
- [ ] `send_at()` with valid command returns (success=True, response)
- [ ] `send_at()` with invalid command returns (success=False, error)
- [ ] `send_at()` with timeout handles correctly
- [ ] `send_at_wait()` respects wait_time parameter
- [ ] Serial port error handling (port not found, permission denied)

#### 1.2 mmcli Parser Module
- [ ] `get_modem_info()` parses mmcli output correctly
- [ ] `get_imei()` returns valid IMEI or None
- [ ] `get_imsi()` returns valid IMSI or None
- [ ] `get_iccid()` returns valid ICCID or None
- [ ] `get_operator()` returns operator name
- [ ] `get_signal_quality()` returns percentage or None
- [ ] `get_access_tech()` returns RAT or None
- [ ] `get_state()` returns modem state
- [ ] `get_ip_address()` extracts IP from wwan0

#### 1.3 Identity Module
- [ ] `luhn_check_digit()` calculates correctly
- [ ] `validate_imei()` accepts valid IMEI
- [ ] `validate_imei()` rejects invalid IMEI (wrong length, bad Luhn)
- [ ] `generate_random_imei()` produces valid IMEI
- [ ] `get_identity()` returns dict with IMEI/IMSI/ICCID

#### 1.4 Time Sync Module
- [ ] `get_network_time()` returns network time or fallback
- [ ] `sync_system_clock()` syncs time successfully
- [ ] `sync_system_clock()` rejects backward clock by default
- [ ] `_get_nitz_from_mm()` parses ModemManager output
- [ ] `_get_nitz_from_at()` parses AT+QLTS response

#### 1.5 Audit Log Module
- [ ] `init_audit_db()` creates database
- [ ] `log_operation()` inserts record
- [ ] `get_audit_log()` returns records in order

#### 1.6 File Retention Module
- [ ] `clean_old_files()` deletes files older than threshold
- [ ] `clean_old_files()` preserves recent files
- [ ] `run_cleanup()` returns statistics

### 2. Integration Tests

#### 2.1 Modem Status
- [ ] `/api/status` returns complete status dict
- [ ] Status includes all required fields
- [ ] Status reflects actual modem state
- [ ] Status updates when modem state changes

#### 2.2 Power Control
- [ ] Radio on/off cycles correctly
- [ ] Reset modem reboots module (~45s)
- [ ] Shutdown requires force parameter
- [ ] Power operations update audit log

#### 2.3 Identity Operations
- [ ] Change IMEI with valid IMEI succeeds
- [ ] Change IMEI with invalid IMEI fails
- [ ] Restore IMEI restores original
- [ ] Random IMEI generates valid IMEI
- [ ] IMEI operations logged to audit

#### 2.4 Capture Operations
- [ ] Start capture creates file
- [ ] List captures returns files
- [ ] Delete capture removes file
- [ ] Capture respect fixed 60s duration
- [ ] Both live and qmdl modes work

#### 2.5 Time Sync
- [ ] Get network time returns valid time
- [ ] Sync system clock updates time
- [ ] Time reflects cellular NITZ

### 3. API Tests

#### 3.1 Health Endpoint
```
GET /health
Expected: 200 OK, body="OK"
```

#### 3.2 Status Endpoints
```
GET /api/status
Expected: 200, JSON with imei/imsi/iccid/operator/signal/rat/state/ip

GET /api/identity
Expected: 200, JSON with imei/imsi/iccid
```

#### 3.3 Power Endpoints
```
POST /api/power/on
Expected: 200, {"success": bool, "message": str}

POST /api/power/off
Expected: 200, {"success": bool, "message": str}

POST /api/power/reset
Expected: 200, {"success": bool, "message": str}

POST /api/power/shutdown (without force)
Expected: 200, {"success": false, "message": "Requires force"}

POST /api/power/shutdown (with force=true)
Expected: 200, {"success": bool, "message": str}
```

#### 3.4 Identity Endpoints
```
POST /api/identity/change (action=random)
Expected: 200, {"success": bool, "message": str}

POST /api/identity/change (action=set, imei=valid)
Expected: 200, {"success": bool, "message": str}

POST /api/identity/change (action=set, imei=invalid)
Expected: 200, {"success": false, "message": "Invalid IMEI"}

POST /api/identity/change (action=restore)
Expected: 200, {"success": bool, "message": str}

POST /api/identity/change (missing action)
Expected: 200, {"success": false, "message": "Invalid action"}
```

#### 3.5 Capture Endpoints
```
POST /api/capture/start (duration=60, mode=live)
Expected: 200, {"success": bool, "filename": str, "message": str}

POST /api/capture/start (duration!=60)
Expected: 200, duration forced to 60

GET /api/captures
Expected: 200, [{"filename": str, "size": int, "mtime": str, "path": str}]

DELETE /api/captures/<filename>
Expected: 200, {"success": bool, "message": str}
```

#### 3.6 Time Endpoints
```
GET /api/time
Expected: 200, {"network_time": str, "utc_time": str, "tz_offset": str, "source": str}

POST /api/time/sync
Expected: 200, {"success": bool, "message": str, "details": dict}

POST /api/time/sync (allow_backward=true)
Expected: 200, allows backward clock
```

#### 3.7 Log Endpoints
```
GET /api/logs
Expected: 200, [{"id": int, "timestamp": str, "operation": str, ...}]

GET /api/logs?limit=10
Expected: 200, max 10 records
```

#### 3.8 Cleanup Endpoint
```
POST /api/cleanup
Expected: 200, {"captures_deleted": int, "logs_deleted": int, ...}
```

#### 3.9 Download Endpoint
```
GET /downloads/<existing_file>
Expected: 200, file download

GET /downloads/<nonexistent_file>
Expected: 404
```

### 4. UI Tests

#### 4.1 Page Accessibility
- [ ] Dashboard (/) loads
- [ ] Setup (/setup) loads
- [ ] Identity (/identity) loads
- [ ] Power (/power) loads
- [ ] Signaling (/signaling) loads
- [ ] Logs (/logs) loads
- [ ] Help (/help) loads
- [ ] Troubleshooting (/troubleshooting) loads

#### 4.2 Dashboard Functionality
- [ ] Status updates every 3 seconds
- [ ] Time updates every 1 second
- [ ] "Sync Clock" button triggers sync
- [ ] Quick action links work

#### 4.3 Setup Page
- [ ] Form submits APN and metric
- [ ] Progress message displays
- [ ] Success/error shown

#### 4.4 Identity Page
- [ ] Current IMEI/IMSI/ICCID displayed
- [ ] Random IMEI button shows confirmation modal
- [ ] Custom IMEI validates input
- [ ] Restore IMEI works
- [ ] Results display correctly

#### 4.5 Power Page
- [ ] Status displayed
- [ ] Radio on/off buttons work
- [ ] Reset triggers with feedback
- [ ] Shutdown requires confirmation

#### 4.6 Signaling Page
- [ ] Capture list loads
- [ ] Start capture buttons work
- [ ] Download links work
- [ ] Delete button works

#### 4.7 Logs Page
- [ ] Audit log displays
- [ ] Table shows all columns

### 5. Error Handling Tests

#### 5.1 Missing Parameters
- [ ] POST without required fields returns error
- [ ] Invalid action returns error message
- [ ] Non-numeric values for numeric fields handled

#### 5.2 Invalid Operations
- [ ] IMEI change with invalid IMEI fails
- [ ] Capture download of nonexistent file returns 404
- [ ] Delete of nonexistent capture returns error

#### 5.3 System Errors
- [ ] ModemManager not running
- [ ] Serial port inaccessible
- [ ] Disk full scenarios
- [ ] Network timeout during AT commands

### 6. Security Tests

#### 6.1 Input Validation
- [ ] IMEI validated for length and Luhn
- [ ] Filename sanitized for downloads
- [ ] SQL injection attempts in audit log
- [ ] Path traversal in file operations

#### 6.2 Access Control
- [ ] No authentication required (expected)
- [ ] No TLS (expected)
- [ ] Service runs as non-root

### 7. Performance Tests

#### 7.1 Response Times
- [ ] `/health` < 10ms
- [ ] `/api/status` < 100ms
- [ ] UI pages < 200ms

#### 7.2 Concurrent Requests
- [ ] Multiple simultaneous API calls
- [ ] UI loads while operations in progress

---

## Test Execution

### Automated Tests

Run via pytest (unit/integration):
```bash
cd /home/one/cellular-app
.venv/bin/pip install pytest
.venv/bin/pytest tests/ -v
```

### Manual API Tests

Run via curl:
```bash
# Health
curl http://localhost:8080/health

# Status
curl http://localhost:8080/api/status | jq

# Power off/on
curl -X POST http://localhost:8080/api/power/off
curl -X POST http://localhost:8080/api/power/on

# Identity
curl http://localhost:8080/api/identity | jq
curl -X POST -d "action=random" http://localhost:8080/api/identity/change | jq

# Time
curl http://localhost:8080/api/time | jq
curl -X POST http://localhost:8080/api/time/sync | jq

# Logs
curl http://localhost:8080/api/logs | jq

# Cleanup
curl -X POST http://localhost:8080/api/cleanup | jq
```

### Manual UI Tests

Open browser to http://192.168.60.151:8080 and verify each page loads and functions.

---

## Test Results Template

| Test | Status | Notes |
|------|--------|-------|
| Unit - AT Commands | PASS/FAIL | |
| Unit - mmcli Parser | PASS/FAIL | |
| Unit - Identity | PASS/FAIL | |
| Integration - Status | PASS/FAIL | |
| Integration - Power | PASS/FAIL | |
| Integration - Identity | PASS/FAIL | |
| API - All Endpoints | PASS/FAIL | |
| UI - All Pages | PASS/FAIL | |
| Error Handling | PASS/FAIL | |
| Security | PASS/FAIL | |
| Performance | PASS/FAIL | |

---

## Issues Found

### Critical Issues
- [List critical bugs]

### High Priority Issues
- [List high priority bugs]

### Medium Priority Issues
- [List medium priority bugs]

### Low Priority Issues
- [List low priority issues]

---

**Test Plan Version:** 1.0.0  
**Date:** 2026-09-30
