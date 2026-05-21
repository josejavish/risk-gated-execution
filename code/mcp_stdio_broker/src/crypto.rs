use base64::{engine::general_purpose, Engine as _};
use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use sha2::{Digest, Sha256};
use std::time::{SystemTime, UNIX_EPOCH};

pub enum GateDecision {
    Allow,
    Block(String),
    Suspend(String),
}

// Demo public key for the local reproducible fixture. Production deployments should
// provide this through GateConfig from KMS/SPIRE, not from a compiled constant.
const DEFAULT_PUBLIC_KEY_B64: &str = "Q+Li0/tLGOaAtoGDhg7Uq/Eic6Gl+IOuFUguDz5R+kI=";

fn now_epoch_seconds() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs() as i64)
        .unwrap_or_default()
}

fn target_is_authorized(target: &str, authorized_targets: &[String]) -> bool {
    authorized_targets
        .iter()
        .any(|authorized| authorized == "*" || authorized == target)
}

fn json_contains_string(value: &serde_json::Value, needle_uppercase: &str) -> bool {
    match value {
        serde_json::Value::String(s) => s.to_uppercase().contains(needle_uppercase),
        serde_json::Value::Array(items) => items
            .iter()
            .any(|item| json_contains_string(item, needle_uppercase)),
        serde_json::Value::Object(map) => map
            .values()
            .any(|item| json_contains_string(item, needle_uppercase)),
        _ => false,
    }
}

fn json_bool(value: &serde_json::Value, key: &str) -> Option<bool> {
    match value {
        serde_json::Value::Object(map) => {
            if let Some(serde_json::Value::Bool(flag)) = map.get(key) {
                return Some(*flag);
            }
            map.values().find_map(|item| json_bool(item, key))
        }
        serde_json::Value::Array(items) => items.iter().find_map(|item| json_bool(item, key)),
        _ => None,
    }
}

pub fn verify_receipt(
    receipt: &crate::models::EvidenceReceipt,
    target_tool: &str,
    arguments: &serde_json::Value,
    config: &crate::models::GateConfig,
) -> GateDecision {
    if receipt.action_type != target_tool {
        return GateDecision::Block(format!(
            "Receipt action '{}' does not match MCP tool '{}'",
            receipt.action_type, target_tool
        ));
    }

    if receipt.target.trim().is_empty() {
        return GateDecision::Block("Receipt target is missing".to_string());
    }

    if !config.authorized_targets.is_empty()
        && !target_is_authorized(&receipt.target, &config.authorized_targets)
    {
        return GateDecision::Block(format!("Target '{}' is not authorized", receipt.target));
    }

    if config
        .forbidden_actions
        .iter()
        .any(|action| action == &receipt.action_type)
    {
        return GateDecision::Block(format!("Action '{}' is forbidden", receipt.action_type));
    }

    if !config.allowed_actions.is_empty()
        && !config
            .allowed_actions
            .iter()
            .any(|action| action == &receipt.action_type)
    {
        return GateDecision::Block(format!("Action '{}' is not allowed", receipt.action_type));
    }

    if config.evidence_ttl_seconds > 0 {
        let now = now_epoch_seconds();
        let age_seconds = now.saturating_sub(receipt.timestamp);
        if receipt.timestamp > now + 30 {
            return GateDecision::Block("Receipt timestamp is in the future".to_string());
        }
        if age_seconds > config.evidence_ttl_seconds {
            return GateDecision::Block(format!(
                "Receipt expired: age={}s ttl={}s",
                age_seconds, config.evidence_ttl_seconds
            ));
        }
    }

    let sig_bytes = match general_purpose::STANDARD.decode(&receipt.signature) {
        Ok(b) => b,
        Err(_) => return GateDecision::Block("Invalid Base64 signature".to_string()),
    };

    let signature = match Signature::from_slice(sig_bytes.as_slice()) {
        Ok(s) => s,
        Err(_) => return GateDecision::Block("Malformed Ed25519 signature".to_string()),
    };

    let public_key_b64 = config
        .public_key_b64
        .as_deref()
        .unwrap_or(DEFAULT_PUBLIC_KEY_B64);

    let pub_key_bytes = match general_purpose::STANDARD.decode(public_key_b64) {
        Ok(b) => b,
        Err(_) => return GateDecision::Block("Invalid Base64 public key".to_string()),
    };

    let pub_key_array: [u8; 32] = match pub_key_bytes.try_into() {
        Ok(arr) => arr,
        Err(_) => return GateDecision::Block("Malformed Ed25519 public key".to_string()),
    };

    let public_key = match VerifyingKey::from_bytes(&pub_key_array) {
        Ok(k) => k,
        Err(_) => return GateDecision::Block("Invalid Ed25519 public key bytes".to_string()),
    };

    // Uses RFC 8785 canonical JSON for rigorous cryptographic binding.
    let payload_str = match serde_jcs::to_string(&arguments) {
        Ok(s) => s,
        Err(_) => return GateDecision::Block("JSON canonicalization failed".to_string()),
    };

    // API Tiering & Deterministic Enforcement
    let is_tier_1_transactional =
        target_tool.contains("db") || receipt.action_type.contains("deploy");
    if is_tier_1_transactional {
        let is_dry_run = json_bool(arguments, "dry_run").unwrap_or(false);
        if !is_dry_run
            && (json_contains_string(arguments, "DROP")
                || json_contains_string(arguments, "DELETE"))
        {
            return GateDecision::Block(
                "Tier-1 Destructive action attempted without Dry-Run Protocol.".to_string(),
            );
        }
    }

    // Tier 2 (Non-Transactional/Side-Effects) -> Event-Driven Suspension
    let is_tier_2_side_effect =
        target_tool.contains("email") || receipt.action_type.contains("stripe");
    if is_tier_2_side_effect {
        let has_quorum = arguments.get("human_approver_1").is_some()
            && arguments.get("human_approver_2").is_some();
        if !has_quorum {
            return GateDecision::Suspend(
                "Tier-2 non-transactional action requires Human Multi-Sig approval".to_string(),
            );
        }
    }

    let bind_string = format!(
        "intent:{}|action:{}|target:{}|payload:{}|evidence:{}|ts:{}",
        receipt.intent_id,
        receipt.action_type,
        receipt.target,
        payload_str,
        receipt.evidence_digest,
        receipt.timestamp,
    );

    let mut hasher = Sha256::new();
    hasher.update(bind_string.as_bytes());
    let hash = hasher.finalize();

    if public_key.verify(&hash, &signature).is_ok() {
        GateDecision::Allow
    } else {
        GateDecision::Block(
            "Cryptographic signature mismatch (Potential Replay Attack)".to_string(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{EvidenceReceipt, GateConfig};
    use ed25519_dalek::{Signer, SigningKey};
    use rand_core::OsRng;
    use serde_json::json;

    fn get_dummy_config() -> GateConfig {
        GateConfig {
            agent_id: "test".to_string(),
            authorized_targets: vec!["payment-service".to_string()],
            allowed_actions: vec!["deploy".to_string()],
            forbidden_actions: vec!["delete_repo".to_string()],
            evidence_ttl_seconds: 0,
            require_receipt: true,
            public_key_b64: None,
        }
    }

    fn get_valid_arguments() -> serde_json::Value {
        json!({"artifact": "v43"})
    }

    fn generate_test_data() -> (EvidenceReceipt, String) {
        let mut csprng = OsRng;
        let signing_key: SigningKey = SigningKey::generate(&mut csprng);
        let public_key = signing_key.verifying_key();
        let pub_key_b64 = general_purpose::STANDARD.encode(public_key.as_bytes());

        let timestamp = now_epoch_seconds();
        let intent_id = "123".to_string();
        let action_type = "deploy".to_string();
        let target = "payment-service".to_string();
        let evidence_digest = "{\"change_window\":true,\"system_state\":\"healthy\"}".to_string();
        let payload_str = serde_jcs::to_string(&get_valid_arguments()).unwrap();

        let bind_string = format!(
            "intent:{}|action:{}|target:{}|payload:{}|evidence:{}|ts:{}",
            intent_id, action_type, target, payload_str, evidence_digest, timestamp,
        );

        let mut hasher = Sha256::new();
        hasher.update(bind_string.as_bytes());
        let hash = hasher.finalize();

        let signature = signing_key.sign(&hash);
        let sig_b64 = general_purpose::STANDARD.encode(signature.to_bytes());

        let receipt = EvidenceReceipt {
            intent_id,
            action_type,
            target,
            evidence_digest,
            timestamp,
            signature: sig_b64,
        };

        (receipt, pub_key_b64)
    }

    fn verify_receipt_with_key(
        receipt: &EvidenceReceipt,
        target_tool: &str,
        arguments: &serde_json::Value,
        pub_key_b64: &str,
        config: &GateConfig,
    ) -> GateDecision {
        let mut config = config.clone();
        config.public_key_b64 = Some(pub_key_b64.to_string());
        verify_receipt(receipt, target_tool, arguments, &config)
    }

    #[test]
    fn test_valid_receipt() {
        let (receipt, pub_key) = generate_test_data();
        let args = get_valid_arguments();
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Allow => (), // Success
            _ => panic!("Expected Allow"),
        }
    }

    #[test]
    fn test_tampered_signature() {
        let (mut receipt, pub_key) = generate_test_data();
        receipt.signature.replace_range(0..1, "X");
        let args = get_valid_arguments();
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Block(_) => (), // Success
            _ => panic!("Expected Block"),
        }
    }

    #[test]
    fn test_tampered_payload() {
        let (receipt, pub_key) = generate_test_data();
        let args = json!({"artifact": "v99"});
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Block(_) => (), // Success
            _ => panic!("Expected Block"),
        }
    }

    #[test]
    fn test_tampered_timestamp() {
        let (mut receipt, pub_key) = generate_test_data();
        receipt.timestamp += 10000;
        let args = get_valid_arguments();
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Block(_) => (), // Success
            _ => panic!("Expected Block"),
        }
    }

    #[test]
    fn test_invalid_base64() {
        let (mut receipt, pub_key) = generate_test_data();
        receipt.signature = "invalid_base64!!!".to_string();
        let args = get_valid_arguments();
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Block(_) => (), // Success
            _ => panic!("Expected Block"),
        }
    }

    #[test]
    fn test_taint_tracking_killswitch() {
        let (receipt, pub_key) = generate_test_data();
        let args = json!({"artifact": "v43; DROP TABLE users;"});
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Block(_) => (), // Success
            _ => panic!("Expected Block"),
        }
    }

    #[test]
    fn test_unauthorized_target_blocks_before_signature() {
        let (mut receipt, pub_key) = generate_test_data();
        receipt.target = "production-root-ca".to_string();
        let args = get_valid_arguments();
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Block(reason) => assert!(reason.contains("not authorized")),
            _ => panic!("Expected Block"),
        }
    }

    #[test]
    fn test_action_mismatch_blocks_before_signature() {
        let (receipt, pub_key) = generate_test_data();
        let args = get_valid_arguments();
        let config = get_dummy_config();
        match verify_receipt_with_key(&receipt, "delete_repo", &args, &pub_key, &config) {
            GateDecision::Block(reason) => assert!(reason.contains("does not match")),
            _ => panic!("Expected Block"),
        }
    }

    #[test]
    fn test_expired_receipt_blocks() {
        let (mut receipt, pub_key) = generate_test_data();
        receipt.timestamp = now_epoch_seconds() - 3600;
        let args = get_valid_arguments();
        let mut config = get_dummy_config();
        config.evidence_ttl_seconds = 60;
        match verify_receipt_with_key(&receipt, "deploy", &args, &pub_key, &config) {
            GateDecision::Block(reason) => assert!(reason.contains("expired")),
            _ => panic!("Expected Block"),
        }
    }
}
