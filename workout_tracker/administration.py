# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""One shared access boundary for application administration, intentionally open.

Settings/Updates routes call this before handling administrative work. A future
reviewed authentication policy can change this one boundary. Today it permits
all LAN requests and creates no accounts, roles, passwords or sessions.
"""
def administrative_access():
    """Allow every request under the explicitly approved trusted-LAN model."""
    return None


def require_administration():
    """Invoke the centralized policy dynamically, making coverage easy to test."""
    return administrative_access()
