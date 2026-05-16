"""Authoritative game rules package.

`model_backend` is the source of truth for game state and rules. Other layers (tracker,
bridge, frontend) must treat it as authoritative and should only adapt/transport data.
"""

__all__ = ["game"]

