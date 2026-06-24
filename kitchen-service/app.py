from flask import Flask, request, jsonify
import json
import time
import random
import os
from datetime import datetime

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

SERVICE_NAME = os.getenv("SERVICE_NAME", "kitchen-service")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

resource = Resource(attributes={
    "service.name": SERVICE_NAME,
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

set_global_textmap(TraceContextTextMapPropagator())

otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

print(f"🔍 OpenTelemetry initialized for {SERVICE_NAME}, exporting to {OTEL_EXPORTER_OTLP_ENDPOINT}", flush=True)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()


@app.route("/cook", methods=["POST"])
def handle_cook():
    """Cook burgers — called via Dapr service invocation from the order workflow."""
    try:
        data = request.get_json()
        order_id = data["order_id"]
        customer_name = data["customer_name"]
        items = data.get("burgers", [])

        print(f"🍔 Kitchen received order #{order_id} for {customer_name}: {items}", flush=True)

        with tracer.start_as_current_span("cook_burgers") as span:
            span.set_attribute("order.id", order_id)
            span.set_attribute("order.customer_name", customer_name)
            span.set_attribute("order.items", json.dumps(items))

            cook_time = random.randint(8, 15)
            span.set_attribute("cook.time_seconds", cook_time)
            print(f"   🍳 Cooking... (will take {cook_time}s)", flush=True)
            time.sleep(cook_time)
            print(f"   🍳 Done!", flush=True)

        completed_at = datetime.now().isoformat()
        print(f"✅ Kitchen completed order #{order_id}", flush=True)

        return jsonify({
            "order_id": order_id,
            "status": "ready",
            "completed_at": completed_at,
        }), 200

    except Exception as e:
        print(f"❌ Kitchen error: {str(e)}", flush=True)
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "kitchen"})


if __name__ == "__main__":
    print("🍔 Kitchen Service starting...")
    app.run(host="0.0.0.0", port=5002)
