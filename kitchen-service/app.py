from flask import Flask, request, jsonify
from dapr.clients import DaprClient
from cloudevents.http import from_http
import json
import time
import random
import os

# OpenTelemetry imports
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Configure OpenTelemetry
SERVICE_NAME = os.getenv("SERVICE_NAME", "kitchen-service")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

resource = Resource(attributes={
    "service.name": SERVICE_NAME,
    "service.version": "1.0.0",
    "deployment.environment": "development"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Set W3C Trace Context propagator (used by Dapr)
set_global_textmap(TraceContextTextMapPropagator())

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

print(f"🔍 OpenTelemetry initialized for {SERVICE_NAME}, exporting to {OTEL_EXPORTER_OTLP_ENDPOINT}", flush=True)

app = Flask(__name__)

# Note: NOT using FlaskInstrumentor to avoid conflicts with Dapr's tracing
# We'll manually create spans and extract context from Dapr's headers
RequestsInstrumentor().instrument()
GrpcInstrumentorClient().instrument()

DAPR_STORE_NAME = "statestore"

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/dapr/subscribe', methods=['GET'])
def subscribe():
    """Tell Dapr what topics we want to subscribe to"""
    subscriptions = [{
        'pubsubname': 'orderpubsub',
        'topic': 'kitchen-orders',
        'route': '/kitchen-orders'
    }]
    print(f"📋 Dapr subscription endpoint called, returning: {subscriptions}", flush=True)
    return jsonify(subscriptions)

def process_order(order_id, customer_name, items):
    """Process the order and publish completion event"""
    try:
        with tracer.start_as_current_span("cook_burgers") as span:
            # Add span attributes
            span.set_attribute("order.id", order_id)
            span.set_attribute("order.customer_name", customer_name)
            span.set_attribute("order.items", json.dumps(items))

            # Simulate cooking time
            cook_time = random.randint(2, 5)
            span.set_attribute("cook.time_seconds", cook_time)
            print(f"   🍳 Cooking... (will take {cook_time}s)", flush=True)
            time.sleep(cook_time)
            print(f"   🍳 Cooking complete!", flush=True)

        # Helper to inject trace context into Dapr pub/sub requests
        def trace_injector():
            headers = {}
            propagate.inject(headers)
            return headers

        # Publish kitchen completion event back to order-service
        with tracer.start_as_current_span("publish_kitchen_completed") as span:
            span.set_attribute("order.id", order_id)
            print(f"   📤 Publishing kitchen-completed event for order #{order_id}", flush=True)
            with DaprClient(headers_callback=trace_injector) as client:
                client.publish_event(
                    pubsub_name="orderpubsub",
                    topic_name="kitchen-completed",
                    data=json.dumps({
                        'order_id': order_id,
                        'completed_at': time.time()
                    })
                )

        print(f"✅ Kitchen completed order #{order_id}", flush=True)

    except Exception as e:
        print(f"❌ Kitchen processing error: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()

@app.route('/kitchen-orders', methods=['POST'])
def handle_kitchen_order():
    """Handle incoming burger orders from pub/sub"""
    try:
        # Extract trace context from incoming headers
        ctx = propagate.extract(request.headers)

        # Debug: Print trace headers
        traceparent = request.headers.get('traceparent')
        print(f"🔍 Received traceparent: {traceparent}", flush=True)

        # Get raw data
        data_bytes = request.get_data()

        # Parse CloudEvent
        event = from_http(request.headers, data_bytes)
        data = json.loads(event.data)

        order_id = data['order_id']
        customer_name = data['customer_name']
        items = data['items']

        print(f"🍔 Kitchen received order #{order_id} for {customer_name}", flush=True)
        print(f"   Items: {items}", flush=True)

        # Use the extracted context for processing
        with trace.get_tracer(__name__).start_as_current_span("handle_kitchen_order", context=ctx):
            print(f"   🔧 About to call process_order()", flush=True)
            process_order(order_id, customer_name, items)
            print(f"   🔧 Finished calling process_order()", flush=True)

        # Return SUCCESS status for Dapr pub/sub (must be empty body or specific format)
        return '', 200

    except Exception as e:
        print(f"❌ Kitchen error: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        # Return DROP status to indicate we can't process this message
        return jsonify({'status': 'DROP'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'kitchen'})

if __name__ == '__main__':
    print("🍔 Kitchen Service starting...")
    print("   Waiting for burger orders...")
    app.run(host='0.0.0.0', port=5002)
