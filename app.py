import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.colors

# ----------------------------------------------------------------------
# App title and description
st.title("Multi‑Cloud Cost Explorer")
st.write("Interactively explore usage and cost across providers, resources and time.")

# Center the tab bar at the top of the page
st.markdown(
    """
    <style>
    div[data-baseweb="tab-list"] {
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Allow uploads of CSV, gzipped CSV, Parquet, Excel and JSON files
uploaded_file = st.file_uploader(
    "Upload a cost data file. Your file should include categories such as Date, Client, Cloud Provider, Resource, Usage Hour, Cost, Region, and Cost Center.",
    type=["csv", "gz", "parquet", "xlsx", "xls", "json"]
)

# Utility to generate color maps dynamically
def generate_color_map(categories):
    palette = plotly.colors.qualitative.Set3
    colors = palette * (len(categories) // len(palette) + 1)
    return {k: v for k, v in zip(categories, colors)}

# Helper function to load the uploaded data file
@st.cache_data
def load_uploaded_file(uploaded_file):
    """Read the uploaded file into a DataFrame based on its file extension."""
    suffix = uploaded_file.name.split(".")[-1].lower()
    if suffix == "csv":
        df = pd.read_csv(uploaded_file)
    elif suffix == "gz":
        # gzipped CSV – pandas infers compression automatically
        df = pd.read_csv(uploaded_file, compression="infer")
    elif suffix == "parquet":
        df = pd.read_parquet(uploaded_file)
    elif suffix in ("xlsx", "xls"):
        df = pd.read_excel(uploaded_file)
    elif suffix == "json":
        df = pd.read_json(uploaded_file)
    else:
        st.error(f"Unsupported file type: {suffix}")
        df = pd.DataFrame()
    # Convert dates if present
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
    return df

# Use the helper to load whichever type of file the user uploads
if uploaded_file is not None:
    data = load_uploaded_file(uploaded_file)
else:
    data = load_uploaded_file(open("data/multi_cloud_usage.csv", "rb"))

# Show the full scrollable dataset 
st.subheader("Dataset")
st.dataframe(data)

# ----------------------------------------------------------------------
# Overall Insights – global filters
st.sidebar.header("Filter data (Overall Insights)")
# Date range filter (only if Date column is present)
if "Date" in data.columns:
    min_date, max_date = data["Date"].min(), data["Date"].max()
    date_range = st.sidebar.date_input("Date range", value=(min_date, max_date))
else:
    date_range = None

# Multi-select filters
if "CloudProvider" in data.columns:
    providers = st.sidebar.multiselect(
        "Cloud providers",
        options=data["CloudProvider"].unique(),
        default=list(data["CloudProvider"].unique()),
    )
else:
    providers = []
if "ResourceType" in data.columns:
    resources = st.sidebar.multiselect(
        "Resource types",
        options=data["ResourceType"].unique(),
        default=list(data["ResourceType"].unique()),
    )
else:
    resources = []

# Apply global filters
filtered = data.copy()
if date_range and "Date" in data.columns:
    filtered = filtered[
        (filtered["Date"] >= pd.to_datetime(date_range[0]))
        & (filtered["Date"] <= pd.to_datetime(date_range[1]))
    ]
if "CloudProvider" in data.columns and providers:
    filtered = filtered[filtered["CloudProvider"].isin(providers)]
if "ResourceType" in data.columns and resources:
    filtered = filtered[filtered["ResourceType"].isin(resources)]

# ----------------------------------------------------------------------
# Tabs: Overall and Client Specific
overall_tab, client_tab = st.tabs(["Overall Insights", "Client Specific Insights"])

# ----------------------------------------------------------------------
# Overall Insights tab
with overall_tab:
    st.subheader("Summary (Overall)")
    col1, col2 = st.columns(2)
    if "CostUSD" in filtered.columns:
        col1.metric("Total cost (USD)", f"${filtered['CostUSD'].sum():,.2f}")
    if "UsageHours" in filtered.columns:
        col2.metric("Average usage (hours)", f"{filtered['UsageHours'].mean():.2f}")

    # Cost by provider
    if "CloudProvider" in filtered.columns and "CostUSD" in filtered.columns:
        provider_costs = (
            filtered.groupby("CloudProvider")["CostUSD"].sum().reset_index()
        )
        provider_color_map = generate_color_map(provider_costs["CloudProvider"].dropna().unique())
        fig_bar = px.bar(
            provider_costs, x="CloudProvider", y="CostUSD", title="Total Cost by Provider",
            color="CloudProvider", color_discrete_map=provider_color_map
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Cost by resource type
    if "ResourceType" in filtered.columns and "CostUSD" in filtered.columns:
        resource_costs = (
            filtered.groupby("ResourceType")["CostUSD"].sum().reset_index()
        )
        resource_color_map = generate_color_map(resource_costs["ResourceType"].dropna().unique())
        fig_pie = px.pie(
            resource_costs,
            names="ResourceType",
            values="CostUSD",
            title="Cost Distribution by Resource",
            color="ResourceType",
            color_discrete_map=resource_color_map,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Cost trend over time
    if "Date" in filtered.columns and "CostUSD" in filtered.columns:
        daily_costs = (
            filtered.groupby("Date")["CostUSD"].sum().reset_index()
        )
        fig_line = px.line(
            daily_costs,
            x="Date",
            y="CostUSD",
            title="Cost Trend Over Time",
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # Cost by region
    if "Region" in filtered.columns and "CostUSD" in filtered.columns:
        region_costs = filtered.groupby("Region")["CostUSD"].sum().reset_index()
        region_color_map = generate_color_map(region_costs["Region"].dropna().unique())
        fig_region = px.bar(
            region_costs, x="Region", y="CostUSD", title="Total Cost by Region",
            color="Region", color_discrete_map=region_color_map
        )
        st.plotly_chart(fig_region, use_container_width=True)

    # Cost by cost center
    if "CostCenter" in filtered.columns and "CostUSD" in filtered.columns:
        cc_costs = filtered.groupby("CostCenter")["CostUSD"].sum().reset_index()
        cc_color_map = generate_color_map(cc_costs["CostCenter"].dropna().unique())
        fig_cc = px.pie(
            cc_costs,
            names="CostCenter",
            values="CostUSD",
            title="Cost Distribution by Cost Center",
            color="CostCenter",
            color_discrete_map=cc_color_map,
        )
        st.plotly_chart(fig_cc, use_container_width=True)

# ----------------------------------------------------------------------
# Client Specific Insights tab
with client_tab:
    st.subheader("Filter by client")
    if "Client" not in data.columns:
        st.warning("The uploaded CSV does not contain a 'Client' column.")
    else:
        unique_clients = sorted(data["Client"].dropna().unique())
        search_query = st.text_input("Search client name")
        filtered_client_list = [c for c in unique_clients if search_query.lower() in c.lower()] if search_query else unique_clients

        if not filtered_client_list:
            st.info("No clients match your search.")
        selected_client = st.selectbox("Select a client", options=filtered_client_list)

        client_data = data[data["Client"] == selected_client]

        if client_data.empty:
            st.info("No data found for the specified client.")
        else:
            st.subheader(f"Summary for {selected_client}")
            c1, c2, c3 = st.columns(3)
            if "CostUSD" in client_data.columns:
                c1.metric("Total cost (USD)", f"${client_data['CostUSD'].sum():,.2f}")
            if "UsageHours" in client_data.columns:
                c2.metric("Average usage (hours)", f"{client_data['UsageHours'].mean():.2f}")
                unit_costs = client_data["CostUSD"] / client_data["UsageHours"]
                c3.metric("Avg. cost per hour (USD)", f"${unit_costs.mean():,.2f}")

            # Cost by provider
            if "CloudProvider" in client_data.columns and "CostUSD" in client_data.columns:
                provider_costs_client = client_data.groupby("CloudProvider")["CostUSD"].sum().reset_index()
                provider_color_map_client = generate_color_map(provider_costs_client["CloudProvider"].dropna().unique())
                fig_bar_client = px.bar(
                    provider_costs_client, x="CloudProvider", y="CostUSD", title="Client Cost by Provider",
                    color="CloudProvider", color_discrete_map=provider_color_map_client
                )
                st.plotly_chart(fig_bar_client, use_container_width=True)

            # Cost by resource type
            if "ResourceType" in client_data.columns and "CostUSD" in client_data.columns:
                resource_costs_client = client_data.groupby("ResourceType")["CostUSD"].sum().reset_index()
                resource_color_map_client = generate_color_map(resource_costs_client["ResourceType"].dropna().unique())
                fig_pie_client = px.pie(
                    resource_costs_client,
                    names="ResourceType",
                    values="CostUSD",
                    title="Client Cost Distribution by Resource",
                    color="ResourceType",
                    color_discrete_map=resource_color_map_client,
                )
                st.plotly_chart(fig_pie_client, use_container_width=True)

            # Cost by region
            if "Region" in client_data.columns and "CostUSD" in client_data.columns:
                region_costs_client = client_data.groupby("Region")["CostUSD"].sum().reset_index()
                region_color_map_client = generate_color_map(region_costs_client["Region"].dropna().unique())
                fig_region_client = px.bar(
                    region_costs_client, x="Region", y="CostUSD", title="Client Cost by Region",
                    color="Region", color_discrete_map=region_color_map_client
                )
                st.plotly_chart(fig_region_client, use_container_width=True)

            # Cost by cost center
            if "CostCenter" in client_data.columns and "CostUSD" in client_data.columns:
                cc_costs_client = client_data.groupby("CostCenter")["CostUSD"].sum().reset_index()
                cc_color_map_client = generate_color_map(cc_costs_client["CostCenter"].dropna().unique())
                fig_cc_client = px.pie(
                    cc_costs_client,
                    names="CostCenter",
                    values="CostUSD",
                    title="Client Cost by Cost Center",
                    color="CostCenter",
                    color_discrete_map=cc_color_map_client,
                )
                st.plotly_chart(fig_cc_client, use_container_width=True)

            # Distribution of cost per hour
            if "UsageHours" in client_data.columns and "CostUSD" in client_data.columns:
                unit_costs_all = client_data["CostUSD"] / client_data["UsageHours"]
                # Fixed color and hide legend to avoid the 'variable' legend item
                hist_color_map = generate_color_map(["CostPerHour"])  # single category for consistent color
                fig_hist = px.histogram(
                    unit_costs_all,
                    nbins=20,
                    title="Distribution of Cost per Usage Hour",
                    labels={"value": "USD per hour"},
                    color_discrete_sequence=[hist_color_map["CostPerHour"]],
                )
                fig_hist.update_layout(showlegend=False)
                st.plotly_chart(fig_hist, use_container_width=True)

            # Top cost drivers
            if "CostUSD" in client_data.columns:
                st.subheader("Top cost drivers (services/resources)")
                top5 = client_data.sort_values(by="CostUSD", ascending=False).head(5).copy()
                if "UsageHours" in top5.columns:
                    top5["CostPerHour"] = top5["CostUSD"] / top5["UsageHours"]
                st.dataframe(top5.reset_index(drop=True))

            # Underutilized resources: high cost per hour & low usage
            if "UsageHours" in client_data.columns and "CostUSD" in client_data.columns:
                client_data = client_data.assign(CostPerHour=client_data["CostUSD"] / client_data["UsageHours"])
                threshold = client_data["UsageHours"].mean() * 0.2
                underutilized = client_data[(client_data["UsageHours"] < threshold) & (client_data["CostUSD"] > 0)].sort_values(by="CostPerHour", ascending=False)
                if not underutilized.empty:
                    st.subheader("Underutilized resources (high cost per hour)")
                    st.dataframe(underutilized[["Date", "CloudProvider", "ResourceType", "UsageHours", "CostUSD", "CostPerHour"]].head(5))
