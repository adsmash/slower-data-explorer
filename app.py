import streamlit as st
import pandas as pd
import plotly.express as px

# App title and description
st.title("Multi‑Cloud Cost Explorer")
st.write("Interactively explore usage and cost across providers, resources and time.")

# Caching function 
@st.cache_data
def load_data(file_path):
    """Load a CSV and convert its Date column to datetime if present."""
    df = pd.read_csv(file_path)
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
    return df


# File upload
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

# Data loading to use caching 
if uploaded_file is not None:
    data = load_data(uploaded_file)
else:
    data = load_data("data/multi_cloud_usage.csv")


# Show a preview of the data
st.subheader("Preview")
st.dataframe(data.head())

# Sidebar filters
st.sidebar.header("Filter data")
# Date range filter (only if Date column is present)
if 'Date' in data.columns:
    min_date, max_date = data['Date'].min(), data['Date'].max()
    date_range = st.sidebar.date_input("Date range", value=(min_date, max_date))
else:
    date_range = None

# Multi‑select filters
providers = st.sidebar.multiselect(
    "Cloud providers",
    options=data['CloudProvider'].unique(),
    default=data['CloudProvider'].unique()
)
resources = st.sidebar.multiselect(
    "Resource types",
    options=data['ResourceType'].unique(),
    default=data['ResourceType'].unique()
)

# Apply filters
filtered = data.copy()
if date_range:
    filtered = filtered[
        (filtered['Date'] >= pd.to_datetime(date_range[0])) &
        (filtered['Date'] <= pd.to_datetime(date_range[1]))
    ]
filtered = filtered[
    filtered['CloudProvider'].isin(providers) &
    filtered['ResourceType'].isin(resources)
]

# Tabs for cleaner layout 
tab1, tab2 = st.tabs(["Visualizations", "Data Table"])

with tab1:
    # Summary metrics
    st.subheader("Summary")
    col1, col2 = st.columns(2)
    col1.metric("Total cost (USD)", f"${filtered['CostUSD'].sum():,.2f}")
    col2.metric("Average usage (hours)", f"{filtered['UsageHours'].mean():.2f}")

    # Charts
    # Cost by provider
    provider_costs = filtered.groupby('CloudProvider')['CostUSD'].sum().reset_index()
    fig_bar = px.bar(provider_costs, x='CloudProvider', y='CostUSD', title='Total Cost by Provider')
    st.plotly_chart(fig_bar, use_container_width=True)

    # Cost by resource type
    resource_costs = filtered.groupby('ResourceType')['CostUSD'].sum().reset_index()
    fig_pie = px.pie(resource_costs, names='ResourceType', values='CostUSD', title='Cost Distribution by Resource')
    st.plotly_chart(fig_pie, use_container_width=True)

    # Cost trend over time
    if 'Date' in filtered.columns:
        daily_costs = filtered.groupby('Date')['CostUSD'].sum().reset_index()
        fig_line = px.line(daily_costs, x='Date', y='CostUSD', title='Cost Trend Over Time')
        st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    # Display the filtered data table
    st.subheader("Filtered data")
    st.dataframe(filtered)

