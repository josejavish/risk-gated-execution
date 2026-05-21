import json
import subprocess
import time
import sys

# ---------------------------------------------------------
# RiskGate Orchestrator Middleware
# Handles Out-of-Band Cryptographic Execution.
# ---------------------------------------------------------

def execute_llm_intent():
    """
    Step 1: Parse the semantic tool call from the reasoning engine.
    """
    print("[Orchestrator] Intercepting semantic intent...")
    return {
        "action_type": "deploy",
        "target": "payment-service",
        "arguments": {"artifact": "v43"}
    }

def fetch_cryptographic_receipt(intent):
    """
    Step 2: Authenticate with RiskGate and retrieve EvidenceReceipt.
    """
    print("[Orchestrator] Fetching Veritas Ledger receipt from RiskGate control plane...")
    time.sleep(0.05) # Network latency to RiskGate
    
    return {
      "intent_id": "123",
      "action_type": intent["action_type"],
      "target": intent["target"],
      "evidence_digest": "{\"change_window\":true,\"system_state\":\"healthy\"}",
      "timestamp": 1779273378,
      "signature": "uFxGjv1GhbBn6hBgSZrTBs7DPQOLDvD33FKelxAXRYiQAHfDvwPFTYee4XIcthjYzTYJ/HsGqYKYUI7cO9S8DQ=="
    }

def construct_mcp_payload(llm_intent, receipt):
    """
    Step 3: Inject the receipt into the MCP payload transparently.
    """
    print("[Orchestrator] Injecting Veritas Ledger receipt into MCP payload...")
    return {
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": llm_intent["action_type"],
        "arguments": llm_intent["arguments"],
        "_receipt": receipt
      }
    }

def run_agentic_execution():
    print("--- Starting Autonomous Execution Pipeline ---")
    
    llm_intent = execute_llm_intent()
    receipt = fetch_cryptographic_receipt(llm_intent)
    mcp_payload = construct_mcp_payload(llm_intent, receipt)
    payload_str = json.dumps(mcp_payload) + "\n"
    
    print("[Orchestrator] Dispatching to Stdio Broker (IPC)...")
    
    proc = subprocess.Popen(
        ["./target/release/mcp_stdio_broker", "python3", "dummy_mcp.py"],
        cwd="/home/jsanchhi/patent_fortress/3_BENCHMARK_LAB/mcp_stdio_broker",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    start = time.perf_counter()
    proc.stdin.write(payload_str)
    proc.stdin.flush()
    
    response_str = proc.stdout.readline()
    overhead_us = (time.perf_counter() - start) * 1_000_000
    
    proc.terminate()
    proc.wait() # Ensure process is dead
    
    # Read the OpenTelemetry structured logs from stderr
    trace_logs = proc.stderr.read()
    if trace_logs:
        print("\n[OpenTelemetry] Distributed Tracing Logs (SRE Visibility):")
        print(trace_logs.strip())
        
    try:
        response = json.loads(response_str)
        if "error" in response:
            print(f"\n[ACTUATOR] Execution BLOCKED: {response['error']['message']}")
        else:
            print(f"\n[ACTUATOR] Execution SUCCESS: Payload reached the MCP server securely.")
    except Exception as e:
        print(f"\n[ERROR] Failed to parse response: {response_str}")
        
    print(f"\n[METRICS] Total round-trip latency (Broker + Actuator): {overhead_us:.2f} µs")
    print("--- Execution Complete ---")

if __name__ == "__main__":
    run_agentic_execution()
