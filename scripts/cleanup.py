#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')

from app.utils.file_retention import run_cleanup

if __name__ == "__main__":
    result = run_cleanup()
    print(f"Cleanup complete: {result}")
