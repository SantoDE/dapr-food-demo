# Quick Setup Summary

## What We Added

✅ **OpenTelemetry tracing** to all three services (order, kitchen, bar)
✅ **W3C Trace Context propagation** for distributed tracing across services
✅ **Jaeger** as the tracing backend
✅ **Automatic startup** of Jaeger via updated run-all.sh script

## Architecture (Simplified)

```
Applications (OTEL SDK) ──┐
   + W3C Trace Context    ├──> Jaeger (port 4317) ──> UI (port 16686)
Dapr Sidecars (OTLP)   ──┘
   + W3C propagation
```

### Distributed Trace Flow

```
order-service (creates trace)
     │ W3C traceparent header
     ├──> Dapr ──> kitchen-service (continues trace)
     └──> Dapr ──> bar-service (continues trace)
               │
               └──> Single unified trace in Jaeger
```

## Quick Start

1. **Install Python dependencies:**

   ```bash
   pip3 install --user -r requirements.txt
   ```

2. **Start everything:**

   ```bash
   ./run-all.sh
   ```

3. **View traces:**
   - Open http://localhost:16686
   - Place some orders at http://localhost:5001
   - Search for traces in Jaeger UI

## What Got Removed

❌ Zipkin (replaced with Jaeger OTLP)
❌ OTEL Collector (not needed for simple setup)

## Files Changed

- `requirements.txt` - Added OTEL packages
- `order-service/app.py` - Added OTEL instrumentation + W3C propagation
- `kitchen-service/app.py` - Added OTEL instrumentation + W3C propagation
- `bar-service/app.py` - Added OTEL instrumentation + W3C propagation
- `components/config.yaml` - Changed from Zipkin to OTLP
- `docker-compose.observability.yaml` - Simplified to just Jaeger
- `run-all.sh` - Auto-starts Jaeger
- `TRACING.md` - Full documentation

## Key Features

🔍 **Automatic instrumentation** - Flask endpoints traced automatically
📊 **Custom spans** - Order creation, cooking, pouring operations
🏷️ **Rich attributes** - Order IDs, customer names, processing times
🔗 **Distributed tracing** - Track requests across all services with W3C Trace Context
📈 **100% sampling** - All requests are traced (dev mode)
🌐 **W3C standard** - Industry-standard trace context propagation
🎯 **Single trace ID** - Complete journey from order to completion in one trace

## How W3C Trace Context Works

### What is W3C Trace Context?

W3C Trace Context is an industry standard for propagating trace information across service boundaries. It uses HTTP headers to carry trace information:

- `traceparent`: Contains trace ID, parent span ID, and trace flags
- `tracestate`: Vendor-specific trace data

### In This Application

1. **order-service** creates a new trace when you place an order
2. Dapr automatically adds `traceparent` header to pub/sub messages
3. **kitchen-service** and **bar-service** extract the trace context
4. All spans are linked by the same trace ID
5. You see ONE complete trace in Jaeger spanning all services

### Code Example

Each service configures the W3C propagator:

```python
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Set W3C Trace Context propagator (used by Dapr)
set_global_textmap(TraceContextTextMapPropagator())
```

This ensures automatic propagation without manual header manipulation!

## Troubleshooting

If services fail to start, make sure dependencies are installed:

```bash
pip3 install --user -r requirements.txt
```

### Missing Dapr Sidecar Traces

If you only see application traces but NOT Dapr sidecar traces in Jaeger:

**Problem**: Dapr configuration missing `protocol: "grpc"` specification

**Fix**: Ensure [components/config.yaml](components/config.yaml) has:
```yaml
spec:
  tracing:
    samplingRate: "1"
    stdout: true       # Enables trace debug output
    otel:
      endpointAddress: "localhost:4317"
      isSecure: false
      protocol: "grpc"  # REQUIRED for OTLP gRPC
```

**Verify**: After restart, you should see Dapr sidecar spans (like `calllocal`, `pubsub.publish`) in Jaeger alongside your application spans.

### Disconnected Traces Across Services

If traces are disconnected across services:
- W3C Trace Context propagator is configured in all services
- Dapr configuration has tracing enabled with correct protocol
- Services are restarted after configuration changes
- Dapr sidecars should create intermediate spans linking pub/sub operations

For more details, see [TRACING.md](TRACING.md)
