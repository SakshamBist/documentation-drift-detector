"""Example Client with parameter rename: timeout_secs was renamed to timeout_ms."""

def connect_to_database(host: str, port: int = 5432, timeout_ms: int = 3000) -> bool:
    """Connect to the primary cluster database."""
    print(f"Connecting to {host}:{port} with timeout {timeout_ms}ms")
    return True
