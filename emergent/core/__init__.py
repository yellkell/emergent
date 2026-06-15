"""Core abstractions: the substrate-independent machinery of emergence."""
from __future__ import annotations

from .device import get_device, describe_device
from .rule import Rule
from .universe import Universe

__all__ = ["get_device", "describe_device", "Rule", "Universe"]
