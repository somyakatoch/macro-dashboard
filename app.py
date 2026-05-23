import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Macro Dashboard", layout="wide")
st.title("Macroeconomic Dashboard")

@st.cache_data
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        file_obj = uploaded_file
    else:
        file_obj = "Master_Macro_Dataset_1980_2026.xlsx"

    df = pd.read_excel(file_obj, sheet_name="Master_Monthly_Data")
    df.columns = df.columns.astype(str).str.strip()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    return df


uploaded_file = st.sidebar.file_uploader(
    "Upload Master Excel File",
    type=["xlsx"]
)

df = load_data(uploaded_file)

indicators = [
    "GDP",
    "Unemployment",
    "Inflation Rate",
    "Policy Rate",
    "Bond Yield",
    "Equity Indices"
]

indicators = [i for i in indicators if i in df.columns]

for col in indicators:
    df[col] = pd.to_numeric(df[col], errors="coerce")

countries = sorted(df["Country"].dropna().unique())

st.sidebar.header("Filters")

selected_countries = st.sidebar.multiselect(
    "Select countries",
    countries,
    default=countries[:2]
)

selected_indicator = st.sidebar.selectbox(
    "Select indicator",
    indicators,
    index=indicators.index("Policy Rate") if "Policy Rate" in indicators else 0
)

start_date = st.sidebar.date_input(
    "Start date",
    df["Date"].min().date()
)

end_date = st.sidebar.date_input(
    "End date",
    df["Date"].max().date()
)

frequency = st.sidebar.selectbox(
    "Frequency",
    ["Original", "Monthly", "Quarterly", "Yearly"],
    index=1
)

smooth_window = st.sidebar.slider(
    "Smoothing window",
    min_value=1,
    max_value=12,
    value=3
)

show_points = st.sidebar.checkbox("Show points", value=False)
show_table = st.sidebar.checkbox("Show data table", value=True)

if not selected_countries:
    st.warning("Please select at least one country.")
    st.stop()

data = df[
    (df["Country"].isin(selected_countries)) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
].copy()

data = data[["Date", "Country", selected_indicator]].dropna()
data[selected_indicator] = pd.to_numeric(data[selected_indicator], errors="coerce")
data = data.dropna(subset=[selected_indicator])

if frequency == "Monthly":
    data["Date"] = data["Date"].dt.to_period("M").dt.to_timestamp()
elif frequency == "Quarterly":
    data["Date"] = data["Date"].dt.to_period("Q").dt.to_timestamp()
elif frequency == "Yearly":
    data["Date"] = data["Date"].dt.to_period("Y").dt.to_timestamp()

data = (
    data
    .groupby(["Country", "Date"], as_index=False)[selected_indicator]
    .mean()
    .sort_values(["Country", "Date"])
)

data["Smoothed Value"] = (
    data
    .groupby("Country")[selected_indicator]
    .transform(lambda x: x.rolling(window=smooth_window, min_periods=1).mean())
)

st.subheader(f"{selected_indicator} vs Time")

if data.empty:
    st.warning("No data available.")
else:
    fig = px.line(
        data,
        x="Date",
        y="Smoothed Value",
        color="Country",
        markers=show_points,
        line_shape="spline",
        title=f"{selected_indicator} Comparison"
    )

    fig.update_traces(connectgaps=False)

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_indicator,
        hovermode="x unified",
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)

st.subheader("Comparison Table")

summary = []

for country in selected_countries:
    temp = data[data["Country"] == country].sort_values("Date")

    if len(temp) >= 2:
        start_value = temp["Smoothed Value"].iloc[0]
        end_value = temp["Smoothed Value"].iloc[-1]
        change = end_value - start_value

        pct_change = (change / start_value) * 100 if start_value != 0 else None

        summary.append({
            "Country": country,
            "Start Date": temp["Date"].iloc[0].date(),
            "End Date": temp["Date"].iloc[-1].date(),
            "Start Value": round(start_value, 2),
            "End Value": round(end_value, 2),
            "Absolute Change": round(change, 2),
            "Percent Change (%)": round(pct_change, 2) if pct_change is not None else "N/A"
        })

summary_df = pd.DataFrame(summary)

if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True)
else:
    st.info("Not enough data for comparison.")

st.subheader("Latest Available Values")

latest_rows = []

for country in selected_countries:
    temp = data[data["Country"] == country].sort_values("Date")

    if not temp.empty:
        latest_rows.append({
            "Country": country,
            "Latest Date": temp["Date"].iloc[-1].date(),
            "Latest Value": round(temp["Smoothed Value"].iloc[-1], 2)
        })

latest_df = pd.DataFrame(latest_rows)

if not latest_df.empty:
    st.dataframe(latest_df, use_container_width=True)

if show_table:
    st.subheader("Cleaned Data Used in Chart")
    st.dataframe(data, use_container_width=True)

st.subheader("Single Country: Multiple Indicators")

single_country = st.selectbox("Select one country", countries)

multi_indicators = st.multiselect(
    "Select indicators",
    indicators,
    default=indicators[:3]
)

country_data = df[
    (df["Country"] == single_country) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
].copy()

if multi_indicators:
    small = country_data[["Date", "Country"] + multi_indicators].copy()

    for col in multi_indicators:
        small[col] = pd.to_numeric(small[col], errors="coerce")

    if frequency == "Monthly":
        small["Date"] = small["Date"].dt.to_period("M").dt.to_timestamp()
    elif frequency == "Quarterly":
        small["Date"] = small["Date"].dt.to_period("Q").dt.to_timestamp()
    elif frequency == "Yearly":
        small["Date"] = small["Date"].dt.to_period("Y").dt.to_timestamp()

    small = (
        small
        .groupby(["Country", "Date"], as_index=False)[multi_indicators]
        .mean()
        .sort_values("Date")
    )

    melted = small.melt(
        id_vars=["Date", "Country"],
        value_vars=multi_indicators,
        var_name="Indicator",
        value_name="Value"
    ).dropna()

    melted["Smoothed Value"] = (
        melted
        .groupby("Indicator")["Value"]
        .transform(lambda x: x.rolling(window=smooth_window, min_periods=1).mean())
    )

    fig2 = px.line(
        melted,
        x="Date",
        y="Smoothed Value",
        color="Indicator",
        markers=show_points,
        line_shape="spline",
        title=f"Indicators for {single_country}"
    )

    fig2.update_traces(connectgaps=False)

    fig2.update_layout(
        xaxis_title="Date",
        yaxis_title="Value",
        hovermode="x unified",
        height=550
    )

    st.plotly_chart(fig2, use_container_width=True)

st.download_button(
    label="Download filtered data as CSV",
    data=data.to_csv(index=False).encode("utf-8"),
    file_name="filtered_macro_dashboard_data.csv",
    mime="text/csv"
)
