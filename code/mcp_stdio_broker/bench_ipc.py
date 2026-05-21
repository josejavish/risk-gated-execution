import subprocess
import time
import json
import statistics

PAYLOAD_STR = json.dumps({
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "deploy",
    "arguments": {"artifact": "v43"},
    "_receipt": {
      "intent_id": "123",
      "action_type": "deploy",
      "target": "payment-service",
      "evidence_digest": "{\"change_window\":true,\"system_state\":\"healthy\"}",
      "timestamp": 1779273378,
      "signature": "uFxGjv1GhbBn6hBgSZrTBs7DPQOLDvD33FKelxAXRYiQAHfDvwPFTYee4XIcthjYzTYJ/HsGqYKYUI7cO9S8DQ=="
    }
  }
}) + "\n"

def run_bench(cmd, iterations=10000):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    
    # warmup
    for _ in range(100):
        proc.stdin.write(PAYLOAD_STR)
        proc.stdin.flush()
        proc.stdout.readline()
        
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        proc.stdin.write(PAYLOAD_STR)
        proc.stdin.flush()
        proc.stdout.readline()
        latencies.append((time.perf_counter() - start) * 1000000) # in microseconds
        
    proc.terminate()
    return latencies

print("Benchmarking Direct IPC (Python dummy)...")
direct_lat = run_bench(["python3", "dummy_mcp.py"])

print("Benchmarking Rust Stdio Broker IPC...")
broker_lat = run_bench(["./target/release/mcp_stdio_broker", "python3", "dummy_mcp.py"])

def print_stats(name, lat):
    lat.sort()
    p50 = lat[int(len(lat)*0.5)]
    p95 = lat[int(len(lat)*0.95)]
    p99 = lat[int(len(lat)*0.99)]
    print(f"--- {name} ---")
    print(f"P50: {p50:.2f} us")
    print(f"P95: {p95:.2f} us")
    print(f"P99: {p99:.2f} us")
    print(f"Avg: {sum(lat)/len(lat):.2f} us\n")

print_stats("Direct Execution", direct_lat)
print_stats("Rust MitM Broker", broker_lat)

broker_p95 = broker_lat[int(len(broker_lat)*0.95)]
direct_p95 = direct_lat[int(len(direct_lat)*0.95)]
overhead = broker_p95 - direct_p95
print(f"OVERHEAD P95: {overhead:.2f} microseconds")
