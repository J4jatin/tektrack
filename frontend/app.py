"""
TekTrack — Streamlit Dashboard
Internal Photomask Production Operations Tracker
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_BASE = "http://localhost:8000"

PRIORITY_COLORS = {"CRITICAL": "🔴", "HIGH": "🟡", "NORMAL": "🟢"}
STATUS_LABELS = [
    "ORDER_RECEIVED", "DESIGN_REVIEW", "MASK_WRITING",
    "QUALITY_CHECK", "APPROVED", "SHIPPED", "DELIVERED"
]
STATUS_NEXT = {
    "ORDER_RECEIVED": "DESIGN_REVIEW",
    "DESIGN_REVIEW": "MASK_WRITING",
    "MASK_WRITING": "QUALITY_CHECK",
    "QUALITY_CHECK": "APPROVED",
    "APPROVED": "SHIPPED",
    "SHIPPED": "DELIVERED",
    "DELIVERED": None,
}

st.set_page_config(
    page_title="TekTrack — Photomask Operations",
    page_icon="🎭",
    layout="wide",
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to TekTrack API. Start it with: `uvicorn main:app --reload`")
        st.stop()
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.text}")
        return None


def api_patch(path: str, json: dict):
    try:
        r = requests.patch(f"{API_BASE}{path}", json=json, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Error: {e.response.json().get('detail', e.response.text)}")
        return None


def api_post(path: str, json: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=json, timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        st.error(f"Error: {e.response.json().get('detail', e.response.text)}")
        return None


# ── Sidebar Navigation ────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Semiconductor_icon.svg/120px-Semiconductor_icon.svg.png", width=60)
    st.title("TekTrack")
    st.caption("Photomask Operations Tracker")
    st.divider()
    page = st.radio("Navigation", ["📊 Dashboard", "📋 Orders", "➕ New Order", "🔍 Order Detail"])
    st.divider()
    st.caption(f"API: {API_BASE}")
    if st.button("🔄 Refresh"):
        st.rerun()


# ── Page: Dashboard ───────────────────────────────────────────────────────────

if page == "📊 Dashboard":
    st.title("📊 Production Dashboard")
    summary = api_get("/analytics/summary")
    pipeline = api_get("/analytics/pipeline")

    if summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Orders", summary["total_orders"])
        c2.metric("🔴 Critical Active", summary["critical_in_progress"])
        c3.metric("✅ Delivered", summary["by_status"].get("DELIVERED", 0))
        c4.metric("🔍 In Quality Check", summary["by_status"].get("QUALITY_CHECK", 0))

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Orders by Status")
            status_df = pd.DataFrame([
                {"Status": k, "Count": v}
                for k, v in summary["by_status"].items() if v > 0
            ])
            if not status_df.empty:
                st.bar_chart(status_df.set_index("Status"))

        with col_right:
            st.subheader("Orders by Customer")
            cust_df = pd.DataFrame([
                {"Customer": k, "Orders": v}
                for k, v in summary["by_customer"].items()
            ])
            if not cust_df.empty:
                st.bar_chart(cust_df.set_index("Customer"))

    if pipeline:
        st.divider()
        st.subheader("🔄 Production Pipeline")
        cols = st.columns(len(STATUS_LABELS))
        for col, status in zip(cols, STATUS_LABELS):
            orders = pipeline.get(status, [])
            col.markdown(f"**{status.replace('_',' ')}**")
            col.markdown(f"`{len(orders)} orders`")
            for o in orders[:3]:
                col.markdown(
                    f"<div style='background:#f0f2f6;border-radius:6px;padding:6px;margin-bottom:4px;font-size:12px'>"
                    f"{PRIORITY_COLORS.get(o['priority'],'')} <b>{o['id']}</b><br>{o['customer']}"
                    f"</div>", unsafe_allow_html=True
                )
            if len(orders) > 3:
                col.caption(f"+{len(orders)-3} more")


# ── Page: Orders List ─────────────────────────────────────────────────────────

elif page == "📋 Orders":
    st.title("📋 All Orders")

    with st.expander("Filters", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        f_status = fc1.selectbox("Status", ["All"] + STATUS_LABELS)
        f_priority = fc2.selectbox("Priority", ["All", "CRITICAL", "HIGH", "NORMAL"])
        f_customer = fc3.text_input("Customer (search)")

    params = {}
    if f_status != "All":
        params["status"] = f_status
    if f_priority != "All":
        params["priority"] = f_priority
    if f_customer:
        params["customer"] = f_customer

    orders = api_get("/orders/", params)
    if orders is not None:
        if not orders:
            st.info("No orders match the current filters.")
        else:
            df = pd.DataFrame(orders)
            df["priority"] = df["priority"].apply(lambda p: f"{PRIORITY_COLORS.get(p,'')} {p}")
            st.dataframe(
                df[["id", "customer", "mask_type", "layer", "quantity", "priority", "status", "engineer", "updated_at"]],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(f"{len(orders)} orders found")


# ── Page: New Order ───────────────────────────────────────────────────────────

elif page == "➕ New Order":
    st.title("➕ Create New Order")

    with st.form("new_order_form"):
        r1c1, r1c2 = st.columns(2)
        order_id = r1c1.text_input("Order ID (e.g. TK-2026-009)", placeholder="TK-2026-009")
        customer = r1c2.text_input("Customer", placeholder="GlobalFoundries Dresden")

        r2c1, r2c2, r2c3 = st.columns(3)
        mask_type = r2c1.selectbox("Mask Type", ["ArF 193nm", "EUV 13.5nm", "DUV 248nm", "i-line 365nm", "Other"])
        layer = r2c2.text_input("Layer", placeholder="Metal1")
        quantity = r2c3.number_input("Quantity", min_value=1, max_value=1000, value=1)

        r3c1, r3c2 = st.columns(2)
        priority = r3c1.selectbox("Priority", ["NORMAL", "HIGH", "CRITICAL"])
        engineer = r3c2.text_input("Engineer", placeholder="M. Wagner")

        notes = st.text_area("Notes", placeholder="Additional information...")
        submitted = st.form_submit_button("Create Order", type="primary")

    if submitted:
        if not all([order_id, customer, layer, engineer]):
            st.error("Please fill in all required fields.")
        else:
            result = api_post("/orders/", {
                "id": order_id,
                "customer": customer,
                "mask_type": mask_type,
                "layer": layer,
                "quantity": int(quantity),
                "priority": priority,
                "engineer": engineer,
                "notes": notes,
            })
            if result:
                st.success(f"Order {result['id']} created successfully!")
                st.json(result)


# ── Page: Order Detail ────────────────────────────────────────────────────────

elif page == "🔍 Order Detail":
    st.title("🔍 Order Detail & Status Update")

    order_id = st.text_input("Enter Order ID", placeholder="TK-2026-001")

    if order_id:
        order = api_get(f"/orders/{order_id}")
        if order:
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", order["status"].replace("_", " "))
            c2.metric("Priority", f"{PRIORITY_COLORS.get(order['priority'],'')} {order['priority']}")
            c3.metric("Quantity", order["quantity"])

            st.subheader("Order Details")
            detail_df = pd.DataFrame([{
                "Customer": order["customer"],
                "Mask Type": order["mask_type"],
                "Layer": order["layer"],
                "Engineer": order["engineer"],
                "Created": order["created_at"][:10],
                "Updated": order["updated_at"][:10],
                "Notes": order["notes"],
            }]).T.rename(columns={0: "Value"})
            st.dataframe(detail_df, use_container_width=True)

            # Status advance
            next_status = STATUS_NEXT.get(order["status"])
            st.subheader("Advance Status")
            if next_status:
                if st.button(f"Advance → {next_status.replace('_',' ')}", type="primary"):
                    result = api_patch(f"/orders/{order_id}/status", {
                        "new_status": next_status,
                        "changed_by": "dashboard"
                    })
                    if result:
                        st.success(f"Status updated to {next_status}")
                        st.rerun()
            else:
                st.info("Order is in final state (DELIVERED).")

            # Status log
            st.subheader("Status History")
            logs = api_get(f"/orders/{order_id}/log")
            if logs:
                log_df = pd.DataFrame(logs)[["old_status", "new_status", "changed_at", "changed_by"]]
                log_df.columns = ["From", "To", "Changed At", "By"]
                st.dataframe(log_df, use_container_width=True, hide_index=True)
