"""
Telemetry module for Pandora Cortex.
Handles OpenTelemetry instrumentation and tracing decorators.
"""
import os
import inspect
from functools import wraps
from typing import Optional, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, Span, ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.context import Context
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import FastAPI

# Define resource attributes
resource = Resource(attributes={
    "service.name": "pandora-cortex",
    "service.version": "0.1.0",
})

# Initialize Tracing
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(__name__)


class ReBACSpanProcessor(SpanProcessor):
    """
    Custom SpanProcessor to attach ReBAC context (Layer ID, User ID)
    to spans for audit filtering in Jaeger/Tempo.
    
    This reads from thread-local context set by ReBACTelemetryMiddleware.
    """
    
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """Called when a span is started. Attach ReBAC attributes if available."""
        # Import here to avoid circular imports
        from app.core.telemetry import _rebac_context
        
        if hasattr(_rebac_context, 'layer_id') and _rebac_context.layer_id:
            span.set_attribute("app.layer_id", _rebac_context.layer_id)
        if hasattr(_rebac_context, 'user_id') and _rebac_context.user_id:
            span.set_attribute("app.user.id", _rebac_context.user_id)
    
    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends."""
        pass
    
    def shutdown(self) -> None:
        """Shuts down the processor."""
        pass
    
    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any buffered spans."""
        return True


# Thread-local storage for ReBAC context
import threading
_rebac_context = threading.local()


class ReBACTelemetryMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract ReBAC headers and store them in thread-local
    storage for the ReBACSpanProcessor to access.
    
    Headers:
        - X-Pandora-Layer-ID: The Knowledge Layer being accessed
        - X-Pandora-User-ID: The authenticated user ID
    """
    
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Extract ReBAC headers
        layer_id = request.headers.get("X-Pandora-Layer-ID", "")
        user_id = request.headers.get("X-Pandora-User-ID", "")
        
        # Also try to get from auth state if headers are empty
        if not user_id and hasattr(request.state, 'user'):
            user_id = getattr(request.state.user, 'id', '') or getattr(request.state.user, 'sub', '')
        
        # Store in thread-local context
        _rebac_context.layer_id = layer_id
        _rebac_context.user_id = user_id
        
        # Also set on current span if available
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            if layer_id:
                current_span.set_attribute("app.layer_id", layer_id)
            if user_id:
                current_span.set_attribute("app.user.id", user_id)
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Clear thread-local context
            _rebac_context.layer_id = None
            _rebac_context.user_id = None


def setup_telemetry(app: FastAPI):
    """
    Configure OpenTelemetry for the FastAPI application.
    Reads OTEL_EXPORTER_OTLP_ENDPOINT from env (default: http://jaeger:4317 for K8s).
    
    NOTE: ReBACTelemetryMiddleware must be added in create_app() BEFORE this is called,
    as middleware cannot be added after the application has started.
    """
    if os.getenv("OTEL_TRACES_EXPORTER") == "none" or os.getenv("TELEMETRY_ENABLED") == "false":
        print("🔭 Telemetry explicitly disabled via environment variables.")
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317")
    
    # Configure OTLP Exporter (GRPC)
    otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Add ReBAC span processor for audit attributes
    rebac_processor = ReBACSpanProcessor()
    tracer_provider.add_span_processor(rebac_processor)
    
    # Auto-instrument FastAPI
    try:
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
        print(f"🔭 Telemetry enabled. Sending traces to {endpoint}")
        print(f"🔐 ReBAC span attributes enabled (app.layer_id, app.user.id)")
    except RuntimeError as e:
        print(f"⚠️ Telemetry instrumentation skipped: {e}")

def trace_span(name: Optional[str] = None):
    """
    Decorator to wrap a function in a custom OTEL span.
    
    Usage:
        @trace_span("custom_operation_name")
        def my_func():
            ...
    """
    def decorator(func):
        span_name = name or func.__name__

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator

