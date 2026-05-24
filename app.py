import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================================
# PAGE CONFIG
# ==========================================

st.set_page_config(
    page_title="Macro Economic Dashboard",
    layout="wide"
)

st.title("Macro Economic Dashboard")

# ==========================================
# LOAD DATA
# ==========================================

@st.cache_data
def load_data(file):

    xls = pd.ExcelFile(file)

    if "Master_Monthly_Data" in xls.sheet_names:

        df = pd.read_excel(
            file,
            sheet_name="Master_Monthly_Data"
        )

    else:

        all_data = []

        for sheet in xls.sheet_names:

            temp = pd.read_excel(
                file,
                sheet_name=sheet
            )

            temp.columns = (
                temp.columns
                .astype(str)
                .str.strip()
            )

            if "Date" in temp.columns:

                temp["Country"] = sheet

                all_data.append(temp)

        df = pd.concat(
            all_data,
            ignore_index=True
        )

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    df = df.dropna(subset=["Date"])

    return df


# ==========================================
# FILE UPLOADER
# ==========================================

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

if uploaded_file is None:

    st.info(
        "Please upload your Excel dataset."
    )

    st.stop()

df = load_data(uploaded_file)

# ==========================================
# INDICATORS
# ==========================================

possible_indicators = [

    "GDP",
    "Unemployment",
    "Inflation Rate",
    "Policy Rate",
    "Bond Yield",
    "Equity Indices"
]

indicators = [

    col for col in possible_indicators
    if col in df.columns
]

# ==========================================
# CONVERT TO NUMERIC
# ==========================================

for col in indicators:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

countries = sorted(
    df["Country"].dropna().unique()
)

# ==========================================
# SIDEBAR
# ==========================================

st.sidebar.header("Dashboard Controls")

selected_countries = st.sidebar.multiselect(
    "Select Countries",
    countries,
    default=countries[:2]
)

selected_indicator = st.sidebar.selectbox(
    "Select Indicator",
    indicators
)

start_date = st.sidebar.date_input(
    "Start Date",
    value=df["Date"].min().date()
)

end_date = st.sidebar.date_input(
    "End Date",
    value=df["Date"].max().date()
)

frequency = st.sidebar.selectbox(
    "Frequency",
    [
        "Monthly",
        "Quarterly",
        "Yearly"
    ]
)

smooth_window = st.sidebar.slider(
    "Smoothing Window",
    min_value=1,
    max_value=12,
    value=1
)

# ==========================================
# FREQUENCY MAP
# ==========================================

freq_map = {

    "Monthly": "ME",
    "Quarterly": "QE",
    "Yearly": "YE"
}

# ==========================================
# FILTER DATA
# ==========================================

filtered_df = df[

    (df["Country"].isin(selected_countries)) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))

].copy()

if filtered_df.empty:

    st.warning(
        "No data available."
    )

    st.stop()

# ==========================================
# RESAMPLE DATA
# ==========================================

all_resampled = []

for country in selected_countries:

    temp = filtered_df[
        filtered_df["Country"] == country
    ].copy()

    temp = temp.set_index("Date")

    temp = temp[indicators].resample(
        freq_map[frequency]
    ).mean()

    temp["Country"] = country

    temp = temp.reset_index()

    all_resampled.append(temp)

plot_df = pd.concat(
    all_resampled,
    ignore_index=True
)

# ==========================================
# SMOOTHING
# ==========================================

if smooth_window > 1:

    plot_df[selected_indicator] = (

        plot_df
        .groupby("Country")[selected_indicator]
        .transform(

            lambda x: x.rolling(
                smooth_window,
                min_periods=1
            ).mean()
        )
    )

# ==========================================
# MAIN CHART
# ==========================================

st.subheader(
    f"{selected_indicator} vs Time"
)

fig = px.line(

    plot_df,
    x="Date",
    y=selected_indicator,
    color="Country",
    markers=True,
    title=f"{selected_indicator} Comparison"
)

fig.update_layout(
    height=600
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ==========================================
# AVERAGE TABLE
# ==========================================

st.subheader(
    "Average Value During Selected Period"
)

avg_table = (

    plot_df
    .groupby("Country")[selected_indicator]
    .mean()
    .reset_index()
)

avg_table.columns = [

    "Country",
    f"Average {selected_indicator}"
]

st.dataframe(
    avg_table,
    use_container_width=True
)

# ==========================================
# COMPARISON TABLE
# ==========================================

st.subheader(
    "Comparison Table"
)

comparison_table = (

    plot_df
    .groupby("Country")[indicators]
    .mean()
    .reset_index()
)

st.dataframe(
    comparison_table,
    use_container_width=True
)

# ==========================================
# COUNTRY COMPARISON CHART
# ==========================================

st.subheader(
    "Country Comparison"
)

comparison_fig = px.line(

    plot_df,
    x="Date",
    y=selected_indicator,
    color="Country",
    markers=False
)

comparison_fig.update_layout(
    height=550
)

st.plotly_chart(
    comparison_fig,
    use_container_width=True
)

# ==========================================
# RAW DATA
# ==========================================

st.subheader(
    "Filtered Data"
)

st.dataframe(
    filtered_df,
    use_container_width=True
)
