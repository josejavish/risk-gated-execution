import sys
import json

def main():
    for line in sys.stdin:
        if not line.strip(): continue
        try:
            req = json.loads(line)
            res = {
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "result": {"status": "success"}
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception:
            pass

if __name__ == "__main__":
    main()
