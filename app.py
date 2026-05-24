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
        df = pd.read_excel(file, sheet_name="Master_Monthly_Data")

    else:
        all_data = []

        for sheet in xls.sheet_names:

            temp = pd.read_excel(file, sheet_name=sheet)

            temp.columns = temp.columns.astype(str).str.strip()

            if "Date" in temp.columns:
                temp["Country"] = sheet
                all_data.append(temp)

        df = pd.concat(all_data, ignore_index=True)

    df.columns = df.columns.astype(str).str.strip()

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    df = df.dropna(subset=["Date"])

    return df


# ==========================================
# FILE UPLOAD
# ==========================================

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

if uploaded_file is None:
    st.info("Please upload your macro dataset Excel file.")
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

# Convert to numeric

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
    st.warning("No data available.")
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
# FULL COMPARISON TABLE
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
# LEADING / LAGGING ANALYSIS
# ==========================================

st.divider()

st.header(
    "Leading, Lagging & Correlated Indicator Analysis"
)

col1, col2, col3 = st.columns(3)

with col1:

    lag_country = st.selectbox(
        "Country",
        countries,
        key="lag_country"
    )

with col2:

    target_indicator = st.selectbox(
        "Target Indicator",
        indicators,
        key="target_indicator"
    )

with col3:

    max_lag = st.slider(
        "Maximum Lead/Lag",
        min_value=1,
        max_value=24,
        value=12
    )

corr_threshold = st.slider(
    "Strong Correlation Threshold",
    min_value=0.1,
    max_value=0.9,
    value=0.5,
    step=0.05
)

# ==========================================
# PREPARE LAG DATA
# ==========================================

lag_df = df[
    (df["Country"] == lag_country) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
].copy()

lag_df = lag_df.sort_values("Date")

lag_df = lag_df.set_index("Date")

lag_df = lag_df[indicators].resample(
    freq_map[frequency]
).mean()

lag_df = lag_df.reset_index()

results = []

# ==========================================
# LEAD LAG CALCULATION
# ==========================================

for indicator in indicators:

    if indicator == target_indicator:
        continue

    temp = lag_df[
        [
            "Date",
            target_indicator,
            indicator
        ]
    ].dropna()

    if len(temp) < max_lag + 5:
        continue

    best_corr = None
    best_lag = None

    for lag in range(
        -max_lag,
        max_lag + 1
    ):

        shifted = temp.copy()

        shifted[
            indicator + "_shifted"
        ] = shifted[indicator].shift(lag)

        corr = shifted[
            target_indicator
        ].corr(
            shifted[indicator + "_shifted"]
        )

        if pd.notna(corr):

            if (
                best_corr is None or
                abs(corr) > abs(best_corr)
            ):

                best_corr = corr
                best_lag = lag

    # Relationship type

    if best_lag < 0:

        relationship = "Leading Indicator"

        explanation = (
            f"{indicator} moves before "
            f"{target_indicator}"
        )

    elif best_lag > 0:

        relationship = "Lagging Indicator"

        explanation = (
            f"{indicator} moves after "
            f"{target_indicator}"
        )

    else:

        relationship = "Coincident / Correlated"

        explanation = (
            f"{indicator} moves together with "
            f"{target_indicator}"
        )

    # Strength

    if abs(best_corr) >= corr_threshold:
        strength = "Strong"
    else:
        strength = "Weak"

    results.append({

        "Country": lag_country,

        "Target Indicator": target_indicator,

        "Compared Indicator": indicator,

        "Best Lag": best_lag,

        "Correlation": round(best_corr, 3),

        "Relationship": relationship,

        "Strength": strength,

        "Explanation": explanation
    })

lag_result_df = pd.DataFrame(results)

# ==========================================
# SHOW RESULT TABLE
# ==========================================

st.subheader(
    "Lead-Lag Result Table"
)

if lag_result_df.empty:

    st.warning(
        "Not enough data available."
    )

else:

    st.dataframe(
        lag_result_df,
        use_container_width=True
    )

# ==========================================
# STRONG RELATIONSHIPS
# ==========================================

st.subheader(
    "Strong Relationships Only"
)

strong_df = lag_result_df[
    lag_result_df["Strength"] == "Strong"
]

if strong_df.empty:

    st.info(
        "No strong relationships found."
    )

else:

    st.dataframe(
        strong_df,
        use_container_width=True
    )

# ==========================================
# LEAD-LAG CHART
# ==========================================

if not lag_result_df.empty:

    st.subheader(
        "Lead-Lag Correlation Chart"
    )

    fig_lag = px.bar(
        lag_result_df,
        x="Compared Indicator",
        y="Correlation",
        color="Relationship",
        text="Best Lag",
        title=(
            f"Lead-Lag Correlation with "
            f"{target_indicator}"
        )
    )

    fig_lag.update_layout(
        height=500
    )

    st.plotly_chart(
        fig_lag,
        use_container_width=True
    )

# ==========================================
# EXPLANATION
# ==========================================

st.subheader(
    "How to Interpret Best Lag"
)

st.markdown("""

### Interpretation

- Best Lag < 0  
→ Compared indicator is LEADING

- Best Lag > 0  
→ Compared indicator is LAGGING

- Best Lag = 0  
→ Indicators move together

---

### Example

If:

Policy Rate vs Inflation Rate

Best Lag = -3

then:

Policy Rate moves around 3 periods before inflation.

---

### Period Meaning

Depends on selected frequency:

- Monthly → months
- Quarterly → quarters
- Yearly → years

""")
