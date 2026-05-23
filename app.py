import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Macro Dashboard", layout="wide")
st.title("Macroeconomic Dashboard")

@st.cache_data
def load_data(uploaded_file=None):
    file_obj = uploaded_file if uploaded_file else "Master_Macro_Dataset_1980_2026.xlsx"

    df = pd.read_excel(file_obj, sheet_name="Master_Monthly_Data")
    df.columns = df.columns.astype(str).str.strip()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    return df


uploaded_file = st.sidebar.file_uploader("Upload Master Excel File", type=["xlsx"])
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

st.sidebar.subheader("Date Filter")

min_date = df["Date"].min()
max_date = df["Date"].max()

date_mode = st.sidebar.radio(
    "Choose date mode",
    ["Full Range", "Custom Range", "Last N Years", "From Year to Year"]
)

if date_mode == "Full Range":
    start_date = min_date
    end_date = max_date

elif date_mode == "Custom Range":
    selected_range = st.sidebar.date_input(
        "Select date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date()
    )

    if len(selected_range) != 2:
        st.warning("Please select both start and end dates.")
        st.stop()

    start_date = pd.to_datetime(selected_range[0])
    end_date = pd.to_datetime(selected_range[1])

elif date_mode == "Last N Years":
    max_years = max(1, max_date.year - min_date.year)

    n_years = st.sidebar.slider(
        "Last how many years?",
        min_value=1,
        max_value=max_years,
        value=min(10, max_years)
    )

    end_date = max_date
    start_date = end_date - pd.DateOffset(years=n_years)

else:
    start_year = st.sidebar.number_input(
        "Start year",
        min_value=int(min_date.year),
        max_value=int(max_date.year),
        value=int(min_date.year)
    )

    end_year = st.sidebar.number_input(
        "End year",
        min_value=int(min_date.year),
        max_value=int(max_date.year),
        value=int(max_date.year)
    )

    if start_year > end_year:
        st.warning("Start year cannot be greater than end year.")
        st.stop()

    start_date = pd.to_datetime(f"{int(start_year)}-01-01")
    end_date = pd.to_datetime(f"{int(end_year)}-12-31")

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
    (df["Date"] >= start_date) &
    (df["Date"] <= end_date)
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
        average_value = temp["Smoothed Value"].mean()
        minimum_value = temp["Smoothed Value"].min()
        maximum_value = temp["Smoothed Value"].max()
        change = end_value - start_value

        pct_change = (change / start_value) * 100 if start_value != 0 else None

        summary.append({
            "Country": country,
            "Start Date": temp["Date"].iloc[0].date(),
            "End Date": temp["Date"].iloc[-1].date(),
            "Start Value": round(start_value, 2),
            "End Value": round(end_value, 2),
            "Average Value During Selected Period": round(average_value, 2),
            "Minimum Value": round(minimum_value, 2),
            "Maximum Value": round(maximum_value, 2),
            "Absolute Change": round(change, 2),
            "Percent Change (%)": round(pct_change, 2) if pct_change is not None else "N/A"
        })

summary_df = pd.DataFrame(summary)

if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True)
else:
    st.info("Not enough data for comparison.")

st.subheader("Year-wise Average")

yearly_avg = data.copy()
yearly_avg["Year"] = yearly_avg["Date"].dt.year

yearly_avg_table = (
    yearly_avg
    .groupby(["Country", "Year"], as_index=False)["Smoothed Value"]
    .mean()
)

yearly_avg_table = yearly_avg_table.rename(
    columns={"Smoothed Value": f"Average {selected_indicator}"}
)

st.dataframe(
    yearly_avg_table.round(2),
    use_container_width=True
)

fig_yearly_avg = px.bar(
    yearly_avg_table,
    x="Year",
    y=f"Average {selected_indicator}",
    color="Country",
    barmode="group",
    title=f"Year-wise Average {selected_indicator}"
)

fig_yearly_avg.update_layout(
    xaxis_title="Year",
    yaxis_title=f"Average {selected_indicator}",
    height=500
)

st.plotly_chart(fig_yearly_avg, use_container_width=True)

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
    (df["Date"] >= start_date) &
    (df["Date"] <= end_date)
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
