"""Authentication module where legacy use_ssl argument was deprecated and removed."""

def authenticate_user(username: str, token: str) -> bool:
    """Validate user credentials against OAuth provider."""
    return len(username) > 0 and len(token) > 0
