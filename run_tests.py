import py_compile
import pytest
import sys

print("Checking compilation of app/replay.py...")
try:
    py_compile.compile("app/replay.py", doraise=True)
    print("SUCCESS: app/replay.py compiled cleanly with zero syntax errors!")
except Exception as e:
    print(f"FAILED: Syntax error in app/replay.py: {e}")
    sys.exit(1)

print("\nRunning pytest test suite...")
exit_code = pytest.main(["-v", "tests"])
sys.exit(exit_code)
