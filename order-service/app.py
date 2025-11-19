from flask import Flask, render_template, request, jsonify
from dapr.clients import DaprClient
from cloudevents.http import from_http
import json
import uuid
from datetime import datetime
import os

# OpenTelemetry imports
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Configure OpenTelemetry
SERVICE_NAME = os.getenv("SERVICE_NAME", "order-service")
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

# Instrument Flask, requests, and gRPC (for Dapr client SDK)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
GrpcInstrumentorClient().instrument()

DAPR_STORE_NAME = "statestore"
PUBSUB_NAME = "orderpubsub"

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        with tracer.start_as_current_span("create_order") as span:
            customer_name = request.form.get('customer_name')
            items = request.form.getlist('items')

            print(f"📝 Received order - Customer: {customer_name}, Items: {items}", flush=True)

            if not items:
                span.set_attribute("error", True)
                return '<div id="order-status" class="error">Please select at least one item!</div>'

            order_id = str(uuid.uuid4())[:8]

            # Separate food and drinks
            burgers = [item for item in items if 'Burger' in item]
            beers = [item for item in items if item in ['Lager', 'IPA', 'Stout', 'Wheat Beer']]

            print(f"📝 Processed - Burgers: {burgers}, Beers: {beers}", flush=True)

            # Add span attributes
            span.set_attribute("order.id", order_id)
            span.set_attribute("order.customer_name", customer_name)
            span.set_attribute("order.burger_count", len(burgers))
            span.set_attribute("order.beer_count", len(beers))

            order = {
                'order_id': order_id,
                'customer_name': customer_name,
                'burgers': burgers,
                'beers': beers,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }

        with DaprClient() as client:
            # Save order to state store
            print(f"💾 Saving order #{order_id} to state store", flush=True)
            client.save_state(
                store_name=DAPR_STORE_NAME,
                key=f"order-{order_id}",
                value=json.dumps(order)
            )
            print(f"✅ Order #{order_id} saved to state store", flush=True)

            # Also maintain a list of order IDs
            order_list_result = client.get_state(
                store_name=DAPR_STORE_NAME,
                key="order-list"
            )

            if order_list_result.data:
                order_list = json.loads(order_list_result.data)
            else:
                order_list = []

            order_list.insert(0, order_id)  # Add to beginning
            order_list = order_list[:10]  # Keep only last 10 orders

            client.save_state(
                store_name=DAPR_STORE_NAME,
                key="order-list",
                value=json.dumps(order_list)
            )

            # Small delay to ensure state is persisted before publishing events
            # This prevents race conditions where subscribers receive events before state is available
            import time
            time.sleep(0.1)  # 100ms should be enough for Redis

        # Helper to inject trace context into Dapr pub/sub requests
        def trace_injector():
            headers = {}
            propagate.inject(headers)
            return headers

        # Publish to kitchen if burgers
        if burgers:
            with tracer.start_as_current_span("publish_to_kitchen") as pub_span:
                pub_span.set_attribute("order.id", order_id)
                pub_span.set_attribute("order.burgers", json.dumps(burgers))
                print(f"📤 Publishing to kitchen-orders: order #{order_id}", flush=True)

                # Create new DaprClient with trace context headers
                with DaprClient(headers_callback=trace_injector) as pub_client:
                    pub_client.publish_event(
                        pubsub_name=PUBSUB_NAME,
                        topic_name="kitchen-orders",
                        data=json.dumps({
                            'order_id': order_id,
                            'customer_name': customer_name,
                            'items': burgers
                        })
                    )
                print(f"✅ Published to kitchen-orders", flush=True)

        # Publish to bar if beers
        if beers:
            with tracer.start_as_current_span("publish_to_bar") as pub_span:
                pub_span.set_attribute("order.id", order_id)
                pub_span.set_attribute("order.beers", json.dumps(beers))
                print(f"📤 Publishing to bar-orders: order #{order_id}", flush=True)

                # Create new DaprClient with trace context headers
                with DaprClient(headers_callback=trace_injector) as pub_client:
                    pub_client.publish_event(
                        pubsub_name=PUBSUB_NAME,
                        topic_name="bar-orders",
                        data=json.dumps({
                            'order_id': order_id,
                            'customer_name': customer_name,
                            'items': beers
                        })
                    )
                print(f"✅ Published to bar-orders", flush=True)

        return f'''<div id="order-status" class="success">
            ✅ Order #{order_id} placed successfully for {customer_name}!<br>
            🍔 Burgers: {len(burgers)} | 🍺 Beers: {len(beers)}
        </div>'''

    except Exception as e:
        return f'<div id="order-status" class="error">Error: {str(e)}</div>'


def _determine_order_status(order):
    """Determine the overall status of an order"""
    kitchen_status = order.get('kitchen_status', 'pending')
    bar_status = order.get('bar_status', 'pending')

    if order['burgers'] and order['beers']:
        if kitchen_status == 'ready' and bar_status == 'ready':
            return 'ready', '✅ Ready'
        elif kitchen_status == 'ready' or bar_status == 'ready':
            return 'preparing', '🔄 Preparing'
        else:
            return 'pending', '⏳ Pending'
    elif order['burgers']:
        status = 'ready' if kitchen_status == 'ready' else 'pending'
        status_text = '✅ Ready' if kitchen_status == 'ready' else '⏳ Cooking'
        return status, status_text
    else:  # only beers
        status = 'ready' if bar_status == 'ready' else 'pending'
        status_text = '✅ Ready' if bar_status == 'ready' else '⏳ Pouring'
        return status, status_text

def _render_order_card(order_id, order):
    """Render a single order card"""
    status, status_text = _determine_order_status(order)
    burgers = ', '.join(order['burgers']) if order['burgers'] else 'None'
    beers = ', '.join(order['beers']) if order['beers'] else 'None'

    return render_template(
        'order_card.html',
        order_id=order_id,
        customer_name=order['customer_name'],
        status=status,
        status_text=status_text,
        burgers=burgers,
        beers=beers
    )

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        with DaprClient() as client:
            # Get list of order IDs
            order_list_result = client.get_state(
                store_name=DAPR_STORE_NAME,
                key="order-list"
            )

            if not order_list_result.data:
                return '<p style="text-align: center; color: #666;">No orders yet. Place your first order above!</p>'

            order_ids = json.loads(order_list_result.data)
            order_cards = []

            for order_id in order_ids:
                # Get each order
                order_result = client.get_state(
                    store_name=DAPR_STORE_NAME,
                    key=f"order-{order_id}"
                )

                if order_result.data:
                    order = json.loads(order_result.data)
                    order_cards.append(_render_order_card(order_id, order))

            return ''.join(order_cards) if order_cards else '<p>No orders found</p>'

    except Exception as e:
        return f'<p>Error loading orders: {str(e)}</p>'

def _update_order_completion(order_id, completed_at, service_type):
    """Private function to handle order completion updates"""
    status_field = f"{service_type}_status"
    completed_field = f"{service_type}_completed_at"

    with DaprClient() as client:
        result = client.get_state(
            store_name=DAPR_STORE_NAME,
            key=f"order-{order_id}"
        )

        if result.data:
            order = json.loads(result.data)
            order[status_field] = 'ready'
            order[completed_field] = completed_at

            client.save_state(
                store_name=DAPR_STORE_NAME,
                key=f"order-{order_id}",
                value=json.dumps(order)
            )
            print(f"✅ Updated order #{order_id} - {service_type} ready", flush=True)

@app.route('/dapr/subscribe', methods=['GET'])
def subscribe():
    """Tell Dapr what topics we want to subscribe to"""
    subscriptions = [
        {
            'pubsubname': 'orderpubsub',
            'topic': 'kitchen-completed',
            'route': '/kitchen-completed'
        },
        {
            'pubsubname': 'orderpubsub',
            'topic': 'bar-completed',
            'route': '/bar-completed'
        }
    ]
    print(f"📋 Order service subscriptions: {subscriptions}", flush=True)
    return jsonify(subscriptions)

@app.route('/kitchen-completed', methods=['POST'])
def handle_kitchen_completed():
    """Handle kitchen completion events"""
    try:
        event = from_http(request.headers, request.get_data())
        data = json.loads(event.data)
        order_id = data['order_id']
        completed_at = data['completed_at']

        print(f"🍔 Received kitchen-completed for order #{order_id}", flush=True)
        _update_order_completion(order_id, completed_at, 'kitchen')

        return '', 200

    except Exception as e:
        print(f"❌ Error handling kitchen-completed: {str(e)}", flush=True)
        return jsonify({'status': 'DROP'}), 200

@app.route('/bar-completed', methods=['POST'])
def handle_bar_completed():
    """Handle bar completion events"""
    try:
        event = from_http(request.headers, request.get_data())
        data = json.loads(event.data)
        order_id = data['order_id']
        completed_at = data['completed_at']

        print(f"🍺 Received bar-completed for order #{order_id}", flush=True)
        _update_order_completion(order_id, completed_at, 'bar')

        return '', 200

    except Exception as e:
        print(f"❌ Error handling bar-completed: {str(e)}", flush=True)
        return jsonify({'status': 'DROP'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
