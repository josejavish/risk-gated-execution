.PHONY: build-broker demo redteam test clean

CARGO_TARGET_DIR ?= /tmp/rge_mcp_stdio_broker_target
BROKER_BIN := $(CARGO_TARGET_DIR)/release/mcp_stdio_broker

build-broker:
	CARGO_TARGET_DIR=$(CARGO_TARGET_DIR) cargo build --release --manifest-path ../mcp_stdio_broker/Cargo.toml

demo: build-broker
	RGE_BROKER_BIN=$(BROKER_BIN) python3 -m demo_deployment_agent.orchestrator

redteam: build-broker
	RGE_BROKER_BIN=$(BROKER_BIN) python3 -m demo_deployment_agent.redteam_runner

test: build-broker
	python3 -m compileall demo_deployment_agent
	RGE_BROKER_BIN=$(BROKER_BIN) python3 -m demo_deployment_agent.orchestrator
	RGE_BROKER_BIN=$(BROKER_BIN) python3 -m demo_deployment_agent.redteam_runner

clean:
	rm -rf out/*.json demo_deployment_agent/__pycache__
