from flask import Flask, render_template, request, jsonify
from dapr.clients import DaprClient
import dapr.ext.workflow as wf
import json
import uuid
from datetime import datetime
import os

# OpenTelemetry imports
from opentelemetry import trace, propagate, context as otel_context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorClient
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

SERVICE_NAME = os.getenv("SERVICE_NAME", "order-service")
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
GrpcInstrumentorClient().instrument()

DAPR_STORE_NAME = "statestore"

# ── Dapr Workflow Runtime ────────────────────────────────────────────────────

wfr = wf.WorkflowRuntime()


def _update_service_status(order_id: str, service: str, completed_at=None):
    """Write kitchen or bar ready-status back into the order state entry."""
    with DaprClient() as client:
        result = client.get_state(store_name=DAPR_STORE_NAME, key=f"order-{order_id}")
        if result.data:
            order = json.loads(result.data)
            order[f"{service}_status"] = "ready"
            order[f"{service}_completed_at"] = completed_at or datetime.now().isoformat()
            client.save_state(
                store_name=DAPR_STORE_NAME,
                key=f"order-{order_id}",
                value=json.dumps(order),
            )


@wfr.activity(name="cook_burgers")
def cook_burgers_activity(ctx: wf.WorkflowActivityContext, order_input: dict):
    order_id = order_input["order_id"]
    parent_ctx = propagate.extract(order_input.get("trace_context", {}))
    with tracer.start_as_current_span("cook_burgers", context=parent_ctx) as span:
        span.set_attribute("order.id", order_id)
        print(f"🍔 [Activity] Calling kitchen-service for order #{order_id}", flush=True)
        carrier = {}
        propagate.inject(carrier)
        with DaprClient() as client:
            resp = client.invoke_method(
                app_id="kitchen-service",
                method_name="cook",
                data=json.dumps(order_input),
                content_type="application/json",
                http_verb="POST",
                metadata=tuple(carrier.items()),
            )
        result = json.loads(resp.data)
        _update_service_status(order_id, "kitchen", result.get("completed_at"))
        print(f"✅ [Activity] cook_burgers done for order #{order_id}", flush=True)
        return result


@wfr.activity(name="pour_beers")
def pour_beers_activity(ctx: wf.WorkflowActivityContext, order_input: dict):
    order_id = order_input["order_id"]
    parent_ctx = propagate.extract(order_input.get("trace_context", {}))
    with tracer.start_as_current_span("pour_beers", context=parent_ctx) as span:
        span.set_attribute("order.id", order_id)
        print(f"🍺 [Activity] Calling bar-service for order #{order_id}", flush=True)
        carrier = {}
        propagate.inject(carrier)
        with DaprClient() as client:
            resp = client.invoke_method(
                app_id="bar-service",
                method_name="pour",
                data=json.dumps(order_input),
                content_type="application/json",
                http_verb="POST",
                metadata=tuple(carrier.items()),
            )
        result = json.loads(resp.data)
        _update_service_status(order_id, "bar", result.get("completed_at"))
        print(f"✅ [Activity] pour_beers done for order #{order_id}", flush=True)
        return result


@wfr.activity(name="complete_order")
def complete_order_activity(ctx: wf.WorkflowActivityContext, input: dict):
    order_id = input["order_id"]
    with DaprClient() as client:
        result = client.get_state(store_name=DAPR_STORE_NAME, key=f"order-{order_id}")
        if result.data:
            order = json.loads(result.data)
            order["status"] = "ready"
            order["completed_at"] = datetime.now().isoformat()
            client.save_state(
                store_name=DAPR_STORE_NAME,
                key=f"order-{order_id}",
                value=json.dumps(order),
            )
    print(f"✅ [Activity] Order #{order_id} marked complete", flush=True)


@wfr.workflow(name="order_workflow")
def order_workflow(ctx: wf.DaprWorkflowContext, order_input: dict):
    """Fan-out kitchen and bar work in parallel, then mark the order complete."""
    order_id = order_input["order_id"]
    burgers = order_input.get("burgers", [])
    beers = order_input.get("beers", [])

    print(f"🎯 [Workflow] Processing order #{order_id}", flush=True)

    tasks = []
    if burgers:
        tasks.append(ctx.call_activity(cook_burgers_activity, input=order_input))
    if beers:
        tasks.append(ctx.call_activity(pour_beers_activity, input=order_input))

    if tasks:
        yield wf.when_all(tasks)

    yield ctx.call_activity(complete_order_activity, input={"order_id": order_id})

    print(f"🎉 [Workflow] Order #{order_id} complete", flush=True)
    return {"status": "completed", "order_id": order_id}


# ── Flask Routes ─────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/orders", methods=["POST"])
def create_order():
    try:
        with tracer.start_as_current_span("create_order") as span:
            customer_name = request.form.get("customer_name")
            items = request.form.getlist("items")

            print(f"📝 Received order - Customer: {customer_name}, Items: {items}", flush=True)

            if not items:
                span.set_attribute("error", True)
                return '<div id="order-status" class="error">Please select at least one item!</div>'

            order_id = str(uuid.uuid4())[:8]

            burgers = [item for item in items if "Burger" in item]
            beers = [item for item in items if item in ["Lager", "IPA", "Stout", "Wheat Beer"]]

            print(f"📝 Processed - Burgers: {burgers}, Beers: {beers}", flush=True)

            span.set_attribute("order.id", order_id)
            span.set_attribute("order.customer_name", customer_name)
            span.set_attribute("order.burger_count", len(burgers))
            span.set_attribute("order.beer_count", len(beers))

            order = {
                "order_id": order_id,
                "customer_name": customer_name,
                "burgers": burgers,
                "beers": beers,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }

        with DaprClient() as client:
            print(f"💾 Saving order #{order_id} to state store", flush=True)
            client.save_state(
                store_name=DAPR_STORE_NAME,
                key=f"order-{order_id}",
                value=json.dumps(order),
            )

            order_list_result = client.get_state(store_name=DAPR_STORE_NAME, key="order-list")
            order_list = json.loads(order_list_result.data) if order_list_result.data else []
            order_list.insert(0, order_id)
            order_list = order_list[:10]
            client.save_state(store_name=DAPR_STORE_NAME, key="order-list", value=json.dumps(order_list))

        carrier = {}
        propagate.inject(carrier)
        order["trace_context"] = carrier

        print(f"🚀 Starting workflow for order #{order_id}", flush=True)
        wf_client = wf.DaprWorkflowClient()
        wf_client.schedule_new_workflow(
            workflow=order_workflow,
            instance_id=order_id,
            input=order,
        )
        print(f"✅ Workflow started for order #{order_id}", flush=True)

        return f'''<div id="order-status" class="success">
            ✅ Order #{order_id} placed for {customer_name}!<br>
            🍔 Burgers: {len(burgers)} | 🍺 Beers: {len(beers)}
        </div>'''

    except Exception as e:
        import traceback
        print(f"❌ Error in create_order: {e}", flush=True)
        traceback.print_exc()
        return f'<div id="order-status" class="error">Error: {str(e)}</div>'


def _determine_order_status(order):
    kitchen_status = order.get("kitchen_status", "pending")
    bar_status = order.get("bar_status", "pending")

    if order["burgers"] and order["beers"]:
        if kitchen_status == "ready" and bar_status == "ready":
            return "ready", "✅ Ready"
        elif kitchen_status == "ready":
            return "preparing", "🍔 Cooked / 🍺 Pouring..."
        elif bar_status == "ready":
            return "preparing", "🍺 Poured / 🍔 Cooking..."
        else:
            return "pending", "⏳ Cooking & Pouring..."
    elif order["burgers"]:
        status = "ready" if kitchen_status == "ready" else "pending"
        status_text = "✅ Ready" if kitchen_status == "ready" else "⏳ Cooking"
        return status, status_text
    else:
        status = "ready" if bar_status == "ready" else "pending"
        status_text = "✅ Ready" if bar_status == "ready" else "⏳ Pouring"
        return status, status_text


def _render_order_card(order_id, order):
    status, status_text = _determine_order_status(order)
    burgers = ", ".join(order["burgers"]) if order["burgers"] else "None"
    beers = ", ".join(order["beers"]) if order["beers"] else "None"

    return render_template(
        "order_card.html",
        order_id=order_id,
        customer_name=order["customer_name"],
        status=status,
        status_text=status_text,
        burgers=burgers,
        beers=beers,
    )


@app.route("/api/orders", methods=["GET"])
def get_orders():
    try:
        with DaprClient() as client:
            order_list_result = client.get_state(store_name=DAPR_STORE_NAME, key="order-list")

            if not order_list_result.data:
                return '<p style="text-align: center; color: #666;">No orders yet. Place your first order above!</p>'

            order_ids = json.loads(order_list_result.data)
            order_cards = []

            for order_id in order_ids:
                order_result = client.get_state(store_name=DAPR_STORE_NAME, key=f"order-{order_id}")
                if order_result.data:
                    order = json.loads(order_result.data)
                    order_cards.append(_render_order_card(order_id, order))

            return "".join(order_cards) if order_cards else "<p>No orders found</p>"

    except Exception as e:
        return f"<p>Error loading orders: {str(e)}</p>"


if __name__ == "__main__":
    wfr.start()
    app.run(host="0.0.0.0", port=5001)
