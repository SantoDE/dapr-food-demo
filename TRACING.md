# OpenTelemetry Tracing Setup

This project now includes comprehensive distributed tracing using OpenTelemetry (OTEL) and Jaeger.

## Architecture

The tracing setup consists of:

1. **Application-level tracing**: Each Python service (order, kitchen, bar) uses OpenTelemetry SDK to create spans
2. **W3C Trace Context propagation**: All services use W3C TraceContext standard to propagate trace context across service boundaries
3. **Dapr tracing**: Dapr sidecars automatically propagate trace context and export traces to Jaeger via OTLP
4. **Jaeger**: Single backend for collecting, storing, and visualizing all traces

### Distributed Trace Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. User places order via web UI                                │
│    order-service creates new trace with unique trace ID        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. order-service publishes to pub/sub                          │
│    Dapr sidecar adds W3C traceparent header to CloudEvent      │
└─────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ▼                       ▼
┌────────────────────────┐  ┌────────────────────────┐
│ 3. kitchen-service     │  │ 3. bar-service         │
│    Extracts trace ctx  │  │    Extracts trace ctx  │
│    Creates child spans │  │    Creates child spans │
└────────────────────────┘  └────────────────────────┘
                │                       │
                └───────────┬───────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Completion events published back to order-service           │
│    All spans linked by same trace ID                           │
│    Full distributed trace visible in Jaeger                    │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Services with OTEL Instrumentation
- **order-service**: Traces order creation, state management, and pub/sub operations
- **kitchen-service**: Traces burger cooking and completion events
- **bar-service**: Traces beer pouring and completion events

### Observability Stack

- **Jaeger All-in-One**: Single container providing trace collection, storage, and UI
  - UI: http://localhost:16686
  - OTLP gRPC: localhost:4317 (for applications and Dapr)
  - OTLP HTTP: localhost:4318

### Trace Context Propagation

All services implement **W3C Trace Context** propagation, which ensures that distributed traces are correctly linked across service boundaries:

**How it works:**

1. **TraceContextTextMapPropagator**: Each service configures the W3C standard propagator
2. **Automatic propagation**: Flask instrumentation automatically extracts `traceparent` headers from incoming HTTP requests
3. **Dapr integration**: Dapr sidecars understand W3C Trace Context and automatically propagate it through:
   - HTTP/gRPC service invocations
   - Pub/sub messages (added to CloudEvent headers)
   - State store operations
4. **Child span creation**: When a service receives a request with trace context, new spans become children of the parent trace

**What this means:**

- A single order creates ONE distributed trace across ALL services
- You can see the complete journey from order placement to completion
- Timing information shows where bottlenecks occur
- Service dependencies are automatically mapped

## Getting Started

### 1. Install Dependencies

First, install the Python dependencies including OpenTelemetry libraries:

```bash
pip install -r requirements.txt
```

### 2. Start Jaeger

Start the Jaeger tracing backend:

```bash
docker compose -f docker-compose.observability.yaml up -d
```

Verify Jaeger is running:

```bash
curl http://localhost:16686
```

### 3. Start the Dapr Applications

Use the existing Dapr multi-app run command:

```bash
dapr run -f dapr.yaml
```

Or use the run script if available:
```bash
./run-all.sh
```

### 4. Access the Jaeger UI

Open your browser and navigate to: [http://localhost:16686](http://localhost:16686)

## Using the Traces

### Viewing Traces in Jaeger

1. Open [http://localhost:16686](http://localhost:16686)
2. Select a service from the dropdown (e.g., "order-service")
3. Click "Find Traces"
4. Click on any trace to see the detailed span timeline

### What You'll See

Each order flow creates a **single distributed trace** showing the complete journey across all services:

#### Trace Structure

```
order-service: POST /api/orders (root span)
├── order-service: create_order
│   ├── order-service: publish_to_kitchen
│   │   └── dapr: invoke kitchen-orders topic
│   │       └── kitchen-service: POST /kitchen-orders
│   │           ├── kitchen-service: cook_burgers (2-5s)
│   │           └── kitchen-service: publish_kitchen_completed
│   │               └── dapr: invoke kitchen-completed topic
│   │                   └── order-service: POST /kitchen-completed
│   └── order-service: publish_to_bar
│       └── dapr: invoke bar-orders topic
│           └── bar-service: POST /bar-orders
│               ├── bar-service: pour_beers (1-3s)
│               └── bar-service: publish_bar_completed
│                   └── dapr: invoke bar-completed topic
│                       └── order-service: POST /bar-completed
```

#### Span Details

1. **Order Creation Span** (order-service)
   - Root span for the entire trace
   - Attributes: `order.id`, `order.customer_name`, `order.burger_count`, `order.beer_count`

2. **Pub/Sub Publishing Spans** (order-service)
   - Separate spans: `publish_to_kitchen` and `publish_to_bar`
   - Attributes: `order.id`, `order.burgers`, `order.beers`

3. **Cooking/Pouring Spans** (kitchen/bar services)
   - Business logic spans: `cook_burgers`, `pour_beers`
   - Attributes: `order.id`, `order.customer_name`, `order.items`, `cook.time_seconds`, `pour.time_seconds`

4. **Completion Publishing Spans** (kitchen/bar services)
   - Spans: `publish_kitchen_completed`, `publish_bar_completed`
   - Event publication back to order service

5. **Dapr Sidecar Spans** (automatic)
   - HTTP/gRPC calls between services
   - State store operations (Redis)
   - Pub/sub message routing

### Custom Span Attributes

The application adds custom attributes to spans:

- `order.id`: Order identifier
- `order.customer_name`: Customer name
- `order.burger_count`: Number of burgers
- `order.beer_count`: Number of beers
- `order.burgers`: List of burger items
- `order.beers`: List of beer items
- `cook.time_seconds`: Time taken to cook
- `pour.time_seconds`: Time taken to pour

## Configuration

### Environment Variables

You can configure the OTLP endpoint for each service:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export SERVICE_NAME="order-service"  # or kitchen-service, bar-service
```

### Dapr Configuration

The Dapr configuration ([components/config.yaml](components/config.yaml)) is set to:
- Use OTLP protocol (gRPC)
- Export to localhost:4317 (Jaeger)
- 100% sampling rate

### W3C Trace Context Configuration

Each service is configured with the W3C Trace Context propagator:

```python
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Set W3C Trace Context propagator (used by Dapr)
set_global_textmap(TraceContextTextMapPropagator())
```

**Why W3C Trace Context?**

- **Industry standard**: W3C Trace Context is the standard for distributed tracing (see [W3C Specification](https://www.w3.org/TR/trace-context/))
- **Dapr native support**: Dapr automatically propagates W3C traceparent headers
- **Vendor neutral**: Works with any tracing backend (Jaeger, Zipkin, cloud providers)
- **CloudEvents integration**: Trace context is preserved in pub/sub messages
- **Automatic propagation**: No manual header manipulation needed

## Troubleshooting

### No traces appearing in Jaeger

1. Check if Jaeger is running:
   ```bash
   docker ps | grep jaeger
   ```

2. Check application logs for OTEL initialization:
   ```
   🔍 OpenTelemetry initialized for order-service, exporting to http://localhost:4317
   ```

3. Verify connectivity to Jaeger:
   ```bash
   curl http://localhost:4317
   ```

4. Check Dapr sidecar logs:
   ```bash
   dapr logs --app-id order-service
   ```

### Services can't connect to OTLP endpoint

If running in Docker, make sure to use the correct hostname:
- From host machine: `localhost:4317`
- From Docker container: `host.docker.internal:4317` (Mac/Windows) or bridge network

### Traces are disconnected

If you see disconnected traces instead of a single distributed trace:

1. **Check W3C Trace Context propagator is configured**: All services should have:
   ```python
   from opentelemetry.propagate import set_global_textmap
   from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

   set_global_textmap(TraceContextTextMapPropagator())
   ```

2. **Verify Dapr configuration**: Ensure `components/config.yaml` has tracing enabled with OTLP

3. **Check logs**: Look for "OpenTelemetry initialized" messages in service logs

4. **Restart services**: Sometimes a fresh restart helps propagate configuration changes

## Advanced Usage

### Adding Custom Spans

To add custom spans in your code:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("my_custom_operation") as span:
    span.set_attribute("custom.attribute", "value")
    # Your code here
```

### Exporting to Other Backends

If you need to send traces to multiple backends or cloud providers, you can:

1. Add an OpenTelemetry Collector as an intermediary
2. Configure it to export to multiple destinations:
   - Zipkin
   - Prometheus (for metrics)
   - Cloud providers (AWS X-Ray, Google Cloud Trace, Azure Monitor, etc.)

For this advanced setup, refer to the [OpenTelemetry Collector documentation](https://opentelemetry.io/docs/collector/).

## Resources

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Dapr Observability](https://docs.dapr.io/operations/observability/)
- [Dapr Distributed Tracing](https://docs.dapr.io/operations/observability/tracing/)
- [OTLP Specification](https://opentelemetry.io/docs/reference/specification/protocol/otlp/)
- [OpenTelemetry Context Propagation](https://opentelemetry.io/docs/instrumentation/python/manual/#context-propagation)
