import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Macro Dashboard", layout="wide")

st.title("Macro Economic Dashboard")

# ---------- Load Excel ----------
@st.cache_data
def load_data():
    file_name = "Book.xlsx"   # change only if your Excel file name is different

    xls = pd.ExcelFile(file_name)
    all_data = []

    for sheet in xls.sheet_names:
        temp = pd.read_excel(file_name, sheet_name=sheet)
        temp.columns = temp.columns.astype(str).str.strip()

        if "Date" in temp.columns:
            temp["Country"] = sheet.strip()
            all_data.append(temp)

    df = pd.concat(all_data, ignore_index=True)

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    return df

df = load_data()

df.columns = df.columns.astype(str).str.strip()

indicators = [
    "GDP",
    "Unemployment",
    "Inflation Rate",
    "Policy Rate",
    "Bond Yield",
    "Equity Indices"
]

indicators = [col for col in indicators if col in df.columns]

for col in indicators:
    df[col] = pd.to_numeric(df[col], errors="coerce")

countries = sorted(df["Country"].dropna().unique())

# ---------- Sidebar Filters ----------
st.sidebar.header("Filters")

selected_countries = st.sidebar.multiselect(
    "Select countries for comparison",
    countries,
    default=countries[:2]
)

selected_indicator = st.sidebar.selectbox(
    "Select indicator",
    indicators
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
    ["Original", "Monthly", "Quarterly", "Yearly"]
)

show_table = st.sidebar.checkbox("Show data table", value=True)

# ---------- Filter Data ----------
filtered = df[
    (df["Country"].isin(selected_countries)) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
].copy()

# ---------- Resampling ----------
if frequency != "Original":
    freq_map = {
        "Monthly": "ME",
        "Quarterly": "QE",
        "Yearly": "YE"
    }

    filtered = (
        filtered
        .set_index("Date")
        .groupby("Country")[selected_indicator]
        .resample(freq_map[frequency])
        .mean()
        .reset_index()
    )

# ---------- Main Chart ----------
st.subheader(f"{selected_indicator} vs Time")

if filtered.empty:
    st.warning("No data available for selected filters.")
else:
    fig = px.line(
        filtered,
        x="Date",
        y=selected_indicator,
        color="Country",
        markers=True,
        title=f"{selected_indicator} Comparison"
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=selected_indicator,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------- Growth / Change Table ----------
st.subheader("Comparison Table")

summary = []

for country in selected_countries:
    temp = filtered[filtered["Country"] == country].sort_values("Date")

    if len(temp) >= 2:
        start_value = temp[selected_indicator].dropna().iloc[0]
        end_value = temp[selected_indicator].dropna().iloc[-1]

        absolute_change = end_value - start_value

        if start_value != 0:
            percent_change = (absolute_change / start_value) * 100
        else:
            percent_change = None

        summary.append({
            "Country": country,
            "Start Value": round(start_value, 2),
            "End Value": round(end_value, 2),
            "Absolute Change": round(absolute_change, 2),
            "Percent Change (%)": round(percent_change, 2) if percent_change is not None else "N/A"
        })

summary_df = pd.DataFrame(summary)

if not summary_df.empty:
    st.dataframe(summary_df, use_container_width=True)
else:
    st.info("Not enough data to calculate comparison.")

# ---------- Raw Data ----------
if show_table:
    st.subheader("Filtered Data")
    st.dataframe(filtered, use_container_width=True)

# ---------- All Indicators Option ----------
st.subheader("Single Country: All Indicators")

single_country = st.selectbox(
    "Select one country",
    countries
)

country_data = df[
    (df["Country"] == single_country) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
].copy()

selected_multi_indicators = st.multiselect(
    "Select indicators",
    indicators,
    default=indicators[:3]
)

if selected_multi_indicators:
    melted = country_data.melt(
        id_vars=["Date", "Country"],
        value_vars=selected_multi_indicators,
        var_name="Indicator",
        value_name="Value"
    )

    fig2 = px.line(
        melted,
        x="Date",
        y="Value",
        color="Indicator",
        markers=True,
        title=f"All Indicators for {single_country}"
    )

    st.plotly_chart(fig2, use_container_width=True)
