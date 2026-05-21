fn main() {
    let payload_str = serde_json::to_string(&serde_json::json!({"artifact": "v43"})).unwrap();
    let bind_string = format!("intent:{}|action:{}|target:{}|payload:{}|evidence:{}|ts:{}",
        "123",
        "deploy",
        "payment-service",
        payload_str,
        "{\"change_window\":true,\"system_state\":\"healthy\"}", 
        1779273378,
    );
    println!("EXPECTED RUST BIND STRING: {}", bind_string);
}
