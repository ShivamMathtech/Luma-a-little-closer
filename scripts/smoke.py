"""Read-only deployment smoke check. Run with backend's Python environment."""
import argparse
import httpx

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url", nargs="?", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    with httpx.Client(timeout=15) as client:
        for path in ("/health", "/ready", "/openapi.json"):
            result = client.get(base + path)
            result.raise_for_status()
            if path == "/openapi.json":
                assert "/api/v1/posts" in result.json()["paths"]
            else:
                assert result.json()["status"] in {"ok", "ready"}
            print(f"PASS {path}")
        result = client.get(base + "/api/v1/auth/me")
        assert result.status_code == 401
        print("PASS unauthenticated requests rejected")
if __name__ == "__main__":
    main()
