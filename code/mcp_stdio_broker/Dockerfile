FROM rust:1.77-slim-bookworm AS builder

WORKDIR /usr/src/app
COPY . .

# Build the release binary
RUN cargo build --release

FROM debian:bookworm-slim

# Install necessary runtime dependencies (e.g., Python for the dummy MCP server in testing)
RUN apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*

# Create an unprivileged user for the MCP server
RUN useradd -ms /bin/bash mcpuser

WORKDIR /app

# Copy the compiled Rust broker
COPY --from=builder /usr/src/app/target/release/mcp_stdio_broker /usr/local/bin/mcp_stdio_broker

# Copy the dummy MCP server for execution
COPY dummy_mcp.py /app/dummy_mcp.py

# Switch to the unprivileged user
USER mcpuser

# In a real environment, the broker wraps the actual MCP server command.
# E.g., CMD ["mcp_stdio_broker", "node", "build/index.js"]
ENTRYPOINT ["mcp_stdio_broker"]
CMD ["python3", "dummy_mcp.py"]