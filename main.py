from pathlib import Path

import pandas as pd
import streamlit as st


DATA_FILE = Path(__file__).parent / "data" / "synthetic_compliance_logs.csv"

ERROR_CATALOG = {
    "OK": (
        "Valid",
        "No issue",
        "The report passed all automated checks.",
        "No action is required.",
    ),
    "MISSING_TAX_ID": (
        "Critical",
        "Missing required data",
        "The regulated entity cannot be identified because its tax ID is missing.",
        "Add the correct tax ID and submit the report again.",
    ),
    "INVALID_TAX_ID": (
        "High",
        "Invalid identifier",
        "The supplied tax ID does not match the accepted format.",
        "Verify the entity's tax ID against the official record.",
    ),
    "INVALID_DATE": (
        "High",
        "Invalid date",
        "A date is missing or uses a format the reporting system cannot accept.",
        "Correct the date to YYYY-MM-DD and resubmit.",
    ),
    "FUTURE_DATE": (
        "High",
        "Invalid reporting period",
        "The report contains a transaction date in the future.",
        "Check the transaction date and reporting period.",
    ),
    "LATE_SUBMISSION": (
        "High",
        "Submission deadline",
        "The report was received after its compliance deadline.",
        "Confirm whether remediation or a late-filing notice is required.",
    ),
    "TOTAL_MISMATCH": (
        "Critical",
        "Financial inconsistency",
        "The declared total does not equal the sum of the underlying transactions.",
        "Reconcile the figures before resubmission.",
    ),
    "NEGATIVE_AMOUNT": (
        "Medium",
        "Invalid amount",
        "A value that must be zero or greater was submitted as a negative amount.",
        "Check whether the value is an error or should be reported as an adjustment.",
    ),
    "INVALID_AMOUNT": (
        "High",
        "Unreadable amount",
        "A financial field contains text or an unsupported number format.",
        "Replace it with a valid numeric amount.",
    ),
    "DUPLICATE_REPORT": (
        "Medium",
        "Possible duplicate",
        "A report with the same identifier appears to have already been submitted.",
        "Confirm the earlier submission before sending another copy.",
    ),
    "MISSING_REPORT_ID": (
        "Critical",
        "Missing report reference",
        "The entry has no report ID, so it cannot be reliably tracked or audited.",
        "Assign the correct report ID and process the entry again.",
    ),
    "MALFORMED_TIMESTAMP": (
        "Medium",
        "Unreadable timestamp",
        "The system cannot determine when the event occurred.",
        "Correct the timestamp and verify the submission sequence.",
    ),
    "CONNECTION_TIMEOUT": (
        "Low",
        "Technical availability",
        "The regulator's service did not respond; the report data may still be correct.",
        "Retry the submission and escalate if the service remains unavailable.",
    ),
    "MALFORMED_PAYLOAD": (
        "High",
        "Unreadable submission",
        "The submitted file or message is damaged or does not follow the required structure.",
        "Generate the file again using the required schema.",
    ),
    "ENCODING_ERROR": (
        "Medium",
        "Text encoding",
        "Some names or descriptions contain characters the receiving system cannot read.",
        "Export the report using UTF-8 encoding and submit it again.",
    ),
    "UNKNOWN_ERROR": (
        "Needs review",
        "Unclassified issue",
        "The system encountered an error that is not yet in the compliance rule catalog.",
        "Send this entry to a technical reviewer before taking legal action.",
    ),
}

REQUIRED_COLUMNS = {
    "timestamp",
    "report_id",
    "entity",
    "source",
    "error_code",
    "technical_message",
}


def enrich_logs(raw: pd.DataFrame) -> pd.DataFrame:
    """Add business-friendly fields without changing the uploaded source data."""
    df = raw.copy().fillna("")
    df["error_code"] = df["error_code"].astype(str).str.strip().str.upper()
    df.loc[df["error_code"] == "", "error_code"] = "UNKNOWN_ERROR"

    details = df["error_code"].map(ERROR_CATALOG)
    fallback = ERROR_CATALOG["UNKNOWN_ERROR"]
    df["severity"] = details.map(lambda value: value[0] if isinstance(value, tuple) else fallback[0])
    df["issue_type"] = details.map(lambda value: value[1] if isinstance(value, tuple) else fallback[1])
    df["business_explanation"] = details.map(
        lambda value: value[2] if isinstance(value, tuple) else fallback[2]
    )
    df["recommended_action"] = details.map(
        lambda value: value[3] if isinstance(value, tuple) else fallback[3]
    )
    df["result"] = df["error_code"].map(lambda code: "Valid" if code == "OK" else "Has issues")
    return df


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    return pd.read_csv(DATA_FILE, dtype=str, keep_default_na=False)


def show_dashboard(df: pd.DataFrame) -> None:
    total = len(df)
    valid = int((df["result"] == "Valid").sum())
    issues = total - valid
    critical = int((df["severity"] == "Critical").sum())

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total entries", f"{total:,}")
    col2.metric("Valid", f"{valid:,}")
    col3.metric("With issues", f"{issues:,}")
    col4.metric("Critical", f"{critical:,}")

    st.subheader("Overview")
    chart1, chart2 = st.columns(2)
    with chart1:
        st.caption("Validation result")
        result_counts = df["result"].value_counts().rename_axis("Result").to_frame("Entries")
        st.bar_chart(result_counts, color="#2E86AB")
    with chart2:
        st.caption("Issues by severity")
        order = ["Critical", "High", "Medium", "Low", "Needs review"]
        severity_counts = (
            df.loc[df["result"] == "Has issues", "severity"]
            .value_counts()
            .reindex(order, fill_value=0)
            .rename_axis("Severity")
            .to_frame("Entries")
        )
        st.bar_chart(severity_counts, color="#D1495B")

    st.caption("Most common issue types")
    issue_counts = (
        df.loc[df["result"] == "Has issues", "issue_type"]
        .value_counts()
        .head(10)
        .sort_values()
        .rename_axis("Issue")
        .to_frame("Entries")
    )
    st.bar_chart(issue_counts, horizontal=True, color="#F4A261")


def main() -> None:
    st.set_page_config(page_title="Compliance Monitor", page_icon="🏢", layout="wide")
    st.title("🏢 Regulatory Compliance Monitor")
    st.write("Technical report errors, translated into clear compliance actions for Legal.")

    with st.sidebar:
        st.header("Data source")
        uploaded = st.file_uploader("Upload a log file", type=["csv"])
        st.caption("Use the included sample data or upload a CSV with the same columns.")

    try:
        raw = pd.read_csv(uploaded, dtype=str, keep_default_na=False) if uploaded else load_sample_data()
    except Exception as exc:
        st.error(f"The CSV could not be read: {exc}")
        st.stop()

    missing = REQUIRED_COLUMNS.difference(raw.columns)
    if missing:
        st.error("The CSV is missing required columns: " + ", ".join(sorted(missing)))
        st.stop()

    df = enrich_logs(raw)

    with st.sidebar:
        st.header("Filters")
        result_filter = st.multiselect("Result", sorted(df["result"].unique()), default=list(df["result"].unique()))
        severity_filter = st.multiselect(
            "Severity", sorted(df["severity"].unique()), default=list(df["severity"].unique())
        )
        entity_filter = st.multiselect("Entity", sorted(df["entity"].unique()))
        search = st.text_input("Search report or message")

    filtered = df[df["result"].isin(result_filter) & df["severity"].isin(severity_filter)]
    if entity_filter:
        filtered = filtered[filtered["entity"].isin(entity_filter)]
    if search:
        searchable = filtered[["report_id", "technical_message", "entity"]].astype(str).agg(" ".join, axis=1)
        filtered = filtered[searchable.str.contains(search, case=False, regex=False)]

    show_dashboard(filtered)

    st.subheader("Compliance entries")
    st.dataframe(
        filtered[
            [
                "timestamp",
                "report_id",
                "entity",
                "result",
                "severity",
                "issue_type",
                "business_explanation",
                "recommended_action",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Inspect one entry")
    if filtered.empty:
        st.info("No entries match the current filters.")
        return
    choices = filtered.index.tolist()
    selected = st.selectbox(
        "Choose a report",
        choices,
        format_func=lambda idx: f"{filtered.loc[idx, 'report_id'] or '(missing ID)'} — {filtered.loc[idx, 'issue_type']}",
    )
    row = filtered.loc[selected]
    left, right = st.columns(2)
    with left:
        st.markdown("**Original technical message**")
        st.code(row["technical_message"] or "(empty message)")
        st.write(f"Source: {row['source']} · Error code: `{row['error_code']}`")
    with right:
        st.markdown(f"**{row['severity']} — {row['issue_type']}**")
        st.write(row["business_explanation"])
        st.info("Recommended action: " + row["recommended_action"])

    st.download_button(
        "Download analyzed results",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="analyzed_compliance_logs.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
