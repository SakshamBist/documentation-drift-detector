"""Example API Service where return type evolved from string to structured dict."""

from typing import Dict, Any

def fetch_user_profile(user_id: str) -> Dict[str, Any]:
    """Fetch user profile metadata."""
    return {"id": user_id, "active": True, "tier": "gold"}
