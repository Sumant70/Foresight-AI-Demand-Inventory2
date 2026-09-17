import streamlit as st
import pandas as pd

# Existing Foresight AI backend
from app import app_state


st.set_page_config(
    page_title="Foresight AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("FORESIGHT AI")
st.sidebar.caption("Demand & Inventory Intelligence")

st.sidebar.divider()

page = st.sidebar.radio(
    "PLATFORM",
    [
        "Overview",
        "Demand Forecast",
        "Inventory",
        "Stockout Risk",
        "Reorder",
        "Products",
        "Data Quality",
        "Model Performance",
    ],
)


# ============================================================
# HELPER
# ============================================================

def dataframe_from_list(data):
    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)


# ============================================================
# OVERVIEW
# ============================================================

if page == "Overview":

    st.title("Executive Overview")
    st.caption(
        "Centralized visibility into sales demand, warehouse inventory "
        "and replenishment urgency."
    )

    data = app_state.overview_payload
    kpi = data.get("kpis", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Products",
            kpi.get("total_products", 0)
        )

    with col2:
        st.metric(
            "Units Sold",
            f'{kpi.get("total_units_sold", 0):,}'
        )

    with col3:
        revenue = kpi.get("total_sales_revenue", 0)
        st.metric(
            "Sales Revenue",
            f"${revenue / 1e9:.2f}B"
        )

    with col4:
        inventory = kpi.get("current_inventory_value", 0)
        st.metric(
            "Inventory Value",
            f"${inventory / 1e6:.1f}M"
        )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Inventory Units",
            f'{kpi.get("current_inventory_units", 0):,}'
        )

    with col2:
        st.metric(
            "Average Daily Demand",
            f'{kpi.get("avg_daily_demand", 0):.1f}'
        )

    with col3:
        st.metric(
            "High Stockout Risk",
            kpi.get("high_stockout_risk_count", 0)
        )

    st.subheader("Inventory Health")

    health = data.get("stock_health_distribution", {})

    if health:
        health_df = pd.DataFrame(
            {
                "Status": list(health.keys()),
                "Products": list(health.values()),
            }
        )

        st.bar_chart(
            health_df.set_index("Status")
        )

    st.success("Foresight AI intelligence pipeline is running successfully.")


# ============================================================
# DEMAND FORECAST
# ============================================================

elif page == "Demand Forecast":

    st.title("Demand Forecasting")
    st.caption(
        "Expected future demand based on historical sales patterns."
    )

    forecasts = getattr(
        app_state.forecast_engine,
        "forecasts",
        {}
    )

    if forecasts:

        sku_list = list(forecasts.keys())

        selected_sku = st.selectbox(
            "Select SKU",
            sku_list
        )

        forecast_data = forecasts[selected_sku]

        st.subheader(f"Forecast — {selected_sku}")

        if isinstance(forecast_data, list):
            df = pd.DataFrame(forecast_data)

            st.dataframe(
                df,
                use_container_width=True
            )

            numeric_columns = df.select_dtypes(
                include="number"
            ).columns

            if len(numeric_columns) > 0:
                st.line_chart(
                    df[numeric_columns]
                )

        else:
            st.json(forecast_data)

    else:
        st.info("Forecast data is not available.")


# ============================================================
# INVENTORY
# ============================================================

elif page == "Inventory":

    st.title("Inventory Health & Coverage")

    inventory = app_state.inventory_intel.inventory_matrix

    df = dataframe_from_list(inventory)

    if not df.empty:

        st.metric(
            "Tracked SKUs",
            len(df)
        )

        st.dataframe(
            df,
            use_container_width=True,
            height=600
        )

    else:
        st.info("Inventory data is not available.")


# ============================================================
# STOCKOUT RISK
# ============================================================

elif page == "Stockout Risk":

    st.title("Stockout Risk Assessment")

    st.caption(
        "Products requiring replenishment attention before stockouts."
    )

    risks = app_state.stockout_engine.risk_results

    df = dataframe_from_list(risks)

    if not df.empty:

        st.metric(
            "Products Analyzed",
            len(df)
        )

        st.dataframe(
            df,
            use_container_width=True,
            height=600
        )

    else:
        st.info("Stockout risk data is not available.")


# ============================================================
# REORDER
# ============================================================

elif page == "Reorder":

    st.title("Reorder Recommendations")

    st.caption(
        "Calculated replenishment quantities, safety stock "
        "and purchase recommendations."
    )

    recommendations = (
        app_state.reorder_engine.recommendations
    )

    df = dataframe_from_list(recommendations)

    if not df.empty:

        st.metric(
            "Reorder Recommendations",
            len(df)
        )

        st.dataframe(
            df,
            use_container_width=True,
            height=600
        )

    else:
        st.info("Reorder data is not available.")


# ============================================================
# PRODUCTS
# ============================================================

elif page == "Products":

    st.title("Product Analytics & ABC/XYZ")

    products = app_state.merged_products

    df = dataframe_from_list(products)

    if not df.empty:

        st.metric(
            "Total Products",
            len(df)
        )

        search = st.text_input(
            "Search SKU or Product"
        )

        if search:

            mask = (
                df["sku"]
                .astype(str)
                .str.contains(search, case=False, na=False)
                |
                df["product_name"]
                .astype(str)
                .str.contains(search, case=False, na=False)
            )

            df = df[mask]

        st.dataframe(
            df,
            use_container_width=True,
            height=600
        )

    else:
        st.info("Product data is not available.")


# ============================================================
# DATA QUALITY
# ============================================================

elif page == "Data Quality":

    st.title("Data Quality & Profiling")

    processor = app_state.processor

    st.write(
        "Raw and processed datasets used by the Foresight AI "
        "intelligence pipeline."
    )

    st.write(
        "Available SKU records:",
        len(getattr(processor, "skus", {}))
    )

    st.success(
        "Data processing pipeline completed."
    )


# ============================================================
# MODEL PERFORMANCE
# ============================================================

elif page == "Model Performance":

    st.title("Model Performance & Benchmarks")

    benchmark = getattr(
        app_state.forecast_engine,
        "benchmark_summary",
        None
    )

    if benchmark:

        if isinstance(benchmark, dict):

            st.json(benchmark)

        else:

            df = dataframe_from_list(benchmark)

            if not df.empty:
                st.dataframe(
                    df,
                    use_container_width=True
                )

    else:
        st.info(
            "Model benchmark information is not available."
        )