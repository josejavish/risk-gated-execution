use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct EvidenceReceipt {
    pub intent_id: String,
    pub action_type: String,
    pub target: String,
    pub evidence_digest: String,
    pub timestamp: i64,
    pub signature: String, // Base64 encoded Ed25519 signature
}

#[derive(Serialize, Deserialize, Debug)]
pub struct ToolCallParams {
    pub name: String,
    pub arguments: serde_json::Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub _receipt: Option<EvidenceReceipt>, // Injected by the agent after talking to the RiskGate
}

#[derive(Serialize, Deserialize, Debug)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: serde_json::Value,
    pub method: String,
    #[serde(default)]
    pub params: Option<ToolCallParams>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: serde_json::Value,
    pub error: JsonRpcError,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct GateConfig {
    pub agent_id: String,
    pub authorized_targets: Vec<String>,
    #[serde(default)]
    pub allowed_actions: Vec<String>,
    #[serde(default)]
    pub forbidden_actions: Vec<String>,
    pub evidence_ttl_seconds: i64,
    pub require_receipt: bool,
    #[serde(default)]
    pub public_key_b64: Option<String>,
}
