.PHONY: all build test bench run docker-build docker-run clean

all: test build

build:
	cargo build --release

test:
	cargo test

bench:
	python3 bench_ipc.py

run:
	python3 orchestrator_middleware.py

docker-build:
	docker build -t mcp_stdio_broker:latest .

docker-run:
	# Run the containerized broker in interactive mode
	docker run -i --rm mcp_stdio_broker:latest

clean:
	cargo clean
	rm -rf target/
