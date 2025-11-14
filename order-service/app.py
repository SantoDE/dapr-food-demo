from flask import Flask, render_template_string, request, jsonify
from dapr.clients import DaprClient
from cloudevents.http import from_http
import json
import uuid
from datetime import datetime

app = Flask(__name__)

DAPR_STORE_NAME = "statestore"
PUBSUB_NAME = "orderpubsub"

# HTML Template with HTMX
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🍔 Burger & Beer Order System</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .menu-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .menu-card {
            border: 2px solid #eee;
            border-radius: 10px;
            padding: 20px;
            background: #f9f9f9;
        }
        .menu-card h3 {
            margin-top: 0;
            color: #667eea;
        }
        .menu-item {
            margin: 10px 0;
        }
        .menu-item label {
            cursor: pointer;
            display: flex;
            align-items: center;
            padding: 10px;
            border-radius: 5px;
            transition: background 0.2s;
        }
        .menu-item label:hover {
            background: white;
        }
        .menu-item input[type="checkbox"] {
            margin-right: 10px;
            width: 20px;
            height: 20px;
        }
        .form-group {
            margin: 20px 0;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .form-group input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 2px solid #eee;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-weight: bold;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        #order-status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }
        #order-status.success {
            background: #d4edda;
            border: 2px solid #c3e6cb;
            color: #155724;
            display: block;
        }
        #order-status.error {
            background: #f8d7da;
            border: 2px solid #f5c6cb;
            color: #721c24;
            display: block;
        }
        .orders-list {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 3px solid #eee;
        }
        .order-card {
            background: #f9f9f9;
            border: 2px solid #eee;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        .order-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .order-id {
            font-weight: bold;
            color: #667eea;
        }
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        .status-pending { background: #fff3cd; color: #856404; }
        .status-preparing { background: #cce5ff; color: #004085; }
        .status-ready { background: #d4edda; color: #155724; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍔🍺 Burger & Beer Order System</h1>
        <p class="subtitle">Powered by Dapr - Demonstrating State Store & Pub/Sub</p>

        <form hx-post="/api/orders" hx-target="#order-status" hx-swap="innerHTML">
            <div class="menu-section">
                <div class="menu-card">
                    <h3>🍔 Burgers</h3>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="Classic Burger">
                            <span>Classic Burger - $8.99</span>
                        </label>
                    </div>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="Cheeseburger">
                            <span>Cheeseburger - $9.99</span>
                        </label>
                    </div>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="Double Bacon Burger">
                            <span>Double Bacon Burger - $12.99</span>
                        </label>
                    </div>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="Veggie Burger">
                            <span>Veggie Burger - $8.99</span>
                        </label>
                    </div>
                </div>

                <div class="menu-card">
                    <h3>🍺 Beers</h3>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="Lager">
                            <span>Lager - $5.99</span>
                        </label>
                    </div>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="IPA">
                            <span>IPA - $6.99</span>
                        </label>
                    </div>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="Stout">
                            <span>Stout - $6.99</span>
                        </label>
                    </div>
                    <div class="menu-item">
                        <label>
                            <input type="checkbox" name="items" value="Wheat Beer">
                            <span>Wheat Beer - $5.99</span>
                        </label>
                    </div>
                </div>
            </div>

            <div class="form-group">
                <label for="customer_name">Customer Name:</label>
                <input type="text" id="customer_name" name="customer_name" required placeholder="Enter your name">
            </div>

            <button type="submit">Place Order 🚀</button>
        </form>

        <div id="order-status"></div>

        <div class="orders-list">
            <h2>Recent Orders</h2>
            <div id="orders" hx-get="/api/orders" hx-trigger="load, every 3s" hx-swap="innerHTML">
                Loading orders...
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        customer_name = request.form.get('customer_name')
        items = request.form.getlist('items')

        if not items:
            return '<div id="order-status" class="error">Please select at least one item!</div>'

        order_id = str(uuid.uuid4())[:8]

        # Separate food and drinks
        burgers = [item for item in items if 'Burger' in item]
        beers = [item for item in items if item in ['Lager', 'IPA', 'Stout', 'Wheat Beer']]

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

            # Publish to kitchen if burgers
            if burgers:
                print(f"📤 Publishing to kitchen-orders: order #{order_id}", flush=True)
                client.publish_event(
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
                print(f"📤 Publishing to bar-orders: order #{order_id}", flush=True)
                client.publish_event(
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
            html = ''

            for order_id in order_ids:
                # Get each order
                order_result = client.get_state(
                    store_name=DAPR_STORE_NAME,
                    key=f"order-{order_id}"
                )

                if order_result.data:
                    order = json.loads(order_result.data)

                    # Determine overall status
                    kitchen_status = order.get('kitchen_status', 'pending')
                    bar_status = order.get('bar_status', 'pending')

                    # Overall status badge
                    if order['burgers'] and order['beers']:
                        if kitchen_status == 'ready' and bar_status == 'ready':
                            status = 'ready'
                            status_text = '✅ Ready'
                        elif kitchen_status == 'ready' or bar_status == 'ready':
                            status = 'preparing'
                            status_text = '🔄 Preparing'
                        else:
                            status = 'pending'
                            status_text = '⏳ Pending'
                    elif order['burgers']:
                        status = 'ready' if kitchen_status == 'ready' else 'pending'
                        status_text = '✅ Ready' if kitchen_status == 'ready' else '⏳ Cooking'
                    else:  # only beers
                        status = 'ready' if bar_status == 'ready' else 'pending'
                        status_text = '✅ Ready' if bar_status == 'ready' else '⏳ Pouring'

                    burgers_html = ', '.join(order['burgers']) if order['burgers'] else 'None'
                    beers_html = ', '.join(order['beers']) if order['beers'] else 'None'

                    html += f'''
                    <div class="order-card">
                        <div class="order-header">
                            <span class="order-id">Order #{order_id} - {order['customer_name']}</span>
                            <span class="status-badge status-{status}">{status_text}</span>
                        </div>
                        <p><strong>🍔 Burgers:</strong> {burgers_html}</p>
                        <p><strong>🍺 Beers:</strong> {beers_html}</p>
                    </div>
                    '''

            return html if html else '<p>No orders found</p>'

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
