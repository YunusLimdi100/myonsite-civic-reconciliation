import py_compile
import sys

try:
    py_compile.compile("app/services.py", doraise=True)
    print("SUCCESS: app/services.py compiled cleanly with zero syntax errors!")
except Exception as e:
    print(f"FAILED: Syntax error in app/services.py: {e}")
    sys.exit(1)
