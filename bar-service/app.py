from flask import Flask, request, jsonify
from dapr.clients import DaprClient
from cloudevents.http import from_http
import json
import time
import random

app = Flask(__name__)

DAPR_STORE_NAME = "statestore"

@app.route('/dapr/subscribe', methods=['GET'])
def subscribe():
    """Tell Dapr what topics we want to subscribe to"""
    subscriptions = [{
        'pubsubname': 'orderpubsub',
        'topic': 'bar-orders',
        'route': '/bar-orders'
    }]
    print(f"📋 Dapr subscription endpoint called, returning: {subscriptions}", flush=True)
    return jsonify(subscriptions)

def process_order(order_id, customer_name, items):
    """Process the order and publish completion event"""
    try:
        # Simulate pouring time
        pour_time = random.randint(1, 3)
        print(f"   🍻 Pouring... (will take {pour_time}s)", flush=True)
        time.sleep(pour_time)
        print(f"   🍻 Pouring complete!", flush=True)

        # Publish bar completion event back to order-service
        print(f"   📤 Publishing bar-completed event for order #{order_id}", flush=True)
        with DaprClient() as client:
            client.publish_event(
                pubsub_name="orderpubsub",
                topic_name="bar-completed",
                data=json.dumps({
                    'order_id': order_id,
                    'completed_at': time.time()
                })
            )

        print(f"✅ Bar completed order #{order_id}", flush=True)

    except Exception as e:
        print(f"❌ Bar processing error: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()

@app.route('/bar-orders', methods=['POST'])
def handle_bar_order():
    """Handle incoming beer orders from pub/sub"""
    try:
        # Get raw data
        data_bytes = request.get_data()

        # Parse CloudEvent
        event = from_http(request.headers, data_bytes)
        data = json.loads(event.data)

        order_id = data['order_id']
        customer_name = data['customer_name']
        items = data['items']

        print(f"🍺 Bar received order #{order_id} for {customer_name}", flush=True)
        print(f"   Items: {items}", flush=True)

        # Process order synchronously
        print(f"   🔧 About to call process_order()", flush=True)
        process_order(order_id, customer_name, items)
        print(f"   🔧 Finished calling process_order()", flush=True)

        # Return SUCCESS status for Dapr pub/sub (must be empty body or specific format)
        return '', 200

    except Exception as e:
        print(f"❌ Bar error: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        # Return DROP status to indicate we can't process this message
        return jsonify({'status': 'DROP'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'bar'})

if __name__ == '__main__':
    print("🍺 Bar Service starting...")
    print("   Waiting for beer orders...")
    app.run(host='0.0.0.0', port=5003)
