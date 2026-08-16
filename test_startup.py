import sys
from fastapi.testclient import TestClient

try:
    from app.main import app
    client = TestClient(app)
    # Test ping / health check or basic endpoint
    res = client.post("/incidents/replay", json={"reports": []})
    assert res.status_code == 200
    print("SUCCESS: FastAPI application successfully imported and responded to HTTP test request!")
except Exception as e:
    print(f"FAILED: FastAPI startup failed: {e}")
    sys.exit(1)
