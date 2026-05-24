# ===============================
# LEADING / LAGGING INDICATOR ANALYSIS
# ===============================

st.subheader("Leading, Lagging & Correlated Indicator Analysis")

target_indicator = st.selectbox(
    "Select Target Indicator",
    indicators,
    index=0
)

max_lag = st.slider(
    "Maximum lag/lead period to test",
    min_value=1,
    max_value=24,
    value=12
)

corr_threshold = st.slider(
    "Correlation threshold",
    min_value=0.1,
    max_value=0.9,
    value=0.5,
    step=0.05
)

selected_country_lag = st.selectbox(
    "Select country for lag analysis",
    countries,
    key="lag_country"
)

lag_df = df[df["Country"] == selected_country_lag].copy()
lag_df = lag_df.sort_values("Date")

results = []

for indicator in indicators:
    if indicator == target_indicator:
        continue

    temp = lag_df[["Date", target_indicator, indicator]].dropna()

    if len(temp) < max_lag + 5:
        continue

    best_corr = None
    best_lag = None

    for lag in range(-max_lag, max_lag + 1):
        shifted = temp.copy()

        shifted[indicator + "_shifted"] = shifted[indicator].shift(lag)

        corr = shifted[target_indicator].corr(
            shifted[indicator + "_shifted"]
        )

        if pd.notna(corr):
            if best_corr is None or abs(corr) > abs(best_corr):
                best_corr = corr
                best_lag = lag

    if best_lag < 0:
        relation = "Leading Indicator"
        explanation = f"{indicator} tends to move before {target_indicator}"
    elif best_lag > 0:
        relation = "Lagging Indicator"
        explanation = f"{indicator} tends to move after {target_indicator}"
    else:
        relation = "Coincident / Correlated Indicator"
        explanation = f"{indicator} moves around the same time as {target_indicator}"

    strength = "Strong" if abs(best_corr) >= corr_threshold else "Weak"

    results.append({
        "Country": selected_country_lag,
        "Target Indicator": target_indicator,
        "Compared Indicator": indicator,
        "Best Lag": best_lag,
        "Correlation": round(best_corr, 3),
        "Relationship": relation,
        "Strength": strength,
        "Explanation": explanation
    })

lag_result_df = pd.DataFrame(results)

st.dataframe(lag_result_df, use_container_width=True)

strong_results = lag_result_df[lag_result_df["Strength"] == "Strong"]

st.markdown("### Strong Leading / Lagging Relationships")

if strong_results.empty:
    st.info("No strong relationship found with the selected threshold.")
else:
    st.dataframe(strong_results, use_container_width=True)

# ===============================
# BAR CHART OF CORRELATION STRENGTH
# ===============================

if not lag_result_df.empty:
    fig_lag = px.bar(
        lag_result_df,
        x="Compared Indicator",
        y="Correlation",
        color="Relationship",
        text="Best Lag",
        title=f"Lead-Lag Correlation with {target_indicator} - {selected_country_lag}"
    )

    fig_lag.update_layout(
        xaxis_title="Compared Indicator",
        yaxis_title="Correlation",
        height=500
    )

    st.plotly_chart(fig_lag, use_container_width=True)
