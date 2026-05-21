use base64::{engine::general_purpose, Engine as _};
use ed25519_dalek::{Signer, SigningKey};
use rand_core::OsRng;
use sha2::{Digest, Sha256};

fn main() {
    let mut csprng = OsRng;
    let signing_key: SigningKey = SigningKey::generate(&mut csprng);
    let public_key = signing_key.verifying_key();
    let pub_key_b64 = general_purpose::STANDARD.encode(public_key.as_bytes());

    let timestamp = 1779273378;
    let intent_id = "123".to_string();
    let action_type = "deploy";
    let target = "payment-service";
    let evidence_digest = "{\"change_window\":true,\"system_state\":\"healthy\"}";
    let payload_str = "{\"artifact\":\"v43\"}";

    let bind_string = format!(
        "intent:{}|action:{}|target:{}|payload:{}|evidence:{}|ts:{}",
        intent_id, action_type, target, payload_str, evidence_digest, timestamp,
    );

    let mut hasher = Sha256::new();
    hasher.update(bind_string.as_bytes());
    let hash = hasher.finalize();

    let signature = signing_key.sign(&hash);
    let sig_b64 = general_purpose::STANDARD.encode(signature.to_bytes());

    println!("PUB_KEY: {}", pub_key_b64);
    println!("SIG: {}", sig_b64);
}
