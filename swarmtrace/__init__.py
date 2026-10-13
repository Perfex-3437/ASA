"""SwarmTrace: local-first tracing for multi-agent Python programs."""

from .interceptor import Tracer
from .storage import TraceStore

__all__ = ["Tracer", "TraceStore"]
__version__ = "0.1.0"
