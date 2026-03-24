import streamlit as st
import pandas as pd
from datetime import datetime

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Fuel Tracker", layout="wide")

# ------------------ CUSTOM UI ------------------
st.markdown("""
    <style>
    .main {background-color: #0f172a; color: white;}
    .stMetric {background-color: #1e293b; padding: 15px; border-radius: 10px;}
    .block-container {padding-top: 1rem;}
    </style>
""", unsafe_allow_html=True)

st.title("⛽ Fuel Tracker")

# ------------------ TEMPLATE DOWNLOAD ------------------
st.subheader("📥 Start Here")

sample_df = pd.DataFrame([
    {"Date": "2026-03-01", "KM": 1000, "Liters": 3, "Total Bill": 300}
])

st.download_button(
    "⬇️ Download Template",
    sample_df.to_csv(index=False).encode("utf-8"),
    "fuel_template.csv",
    "text/csv"
)

st.info("📌 Supports both formats: 2026-03-01 OR 01-03-2026")

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader("📂 Upload CSV", type=["csv"])

if uploaded_file:
    # AUTO detect separator (comma, tab, etc.)
    df = pd.read_csv(uploaded_file, sep=None, engine="python")
else:
    df = pd.DataFrame(columns=["Date", "KM", "Liters", "Total Bill"])

# ------------------ VALIDATION ------------------
required_cols = ["Date", "KM", "Liters", "Total Bill"]

if len(df) > 0 and not all(col in df.columns for col in required_cols):
    st.error("❌ Invalid CSV format. Use template.")
    st.stop()

# ------------------ AUTO CLEAN ------------------
if len(df) > 0:
    # Smart date parsing (handles Indian + standard format)
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    # Convert numeric safely
    for col in ["KM", "Liters", "Total Bill"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Find bad rows
    bad_rows = df[df.isnull().any(axis=1)]

    if len(bad_rows) > 0:
        st.warning("⚠️ Some rows have invalid data and will be ignored")
        st.dataframe(bad_rows, width="stretch")

    # Remove bad rows
    df = df.dropna()

# ------------------ ADD ENTRY ------------------
st.subheader("➕ Add Entry")

with st.form("add"):
    c1, c2, c3, c4 = st.columns(4)

    date = c1.date_input("Date", datetime.today())
    km = c2.number_input("KM", min_value=0.0)
    liters = c3.number_input("Liters", min_value=0.0)
    amount = c4.number_input("₹", min_value=0.0)

    if st.form_submit_button("Add"):
        new = pd.DataFrame([{
            "Date": str(date),
            "KM": km,
            "Liters": liters,
            "Total Bill": amount
        }])
        df = pd.concat([df, new], ignore_index=True)
        st.success("Added!")

# ------------------ CALCULATIONS ------------------
if len(df) > 0:
    df = df.sort_values("Date")

    df["Distance"] = df["KM"].diff()
    df["Avg"] = df["Distance"] / df["Liters"]
    df["₹/KM"] = df["Total Bill"] / df["Distance"]

    df["Entry"] = range(1, len(df) + 1)

    # Summary
    total_distance = df["Distance"].sum()
    total_liters = df["Liters"].sum()
    overall = total_distance / total_liters if total_liters else 0

    last_avg = df.iloc[-1]["Avg"]

    col1, col2 = st.columns(2)
    col1.metric("🚗 Last Avg", f"{last_avg:.2f} km/l")
    col2.metric("📊 Overall Avg", f"{overall:.2f} km/l")

    # ------------------ FILTER ------------------
    st.subheader("📅 Filter")

    col1, col2 = st.columns(2)
    start = col1.date_input("From", df["Date"].min())
    end = col2.date_input("To", df["Date"].max())

    df_f = df[(df["Date"] >= pd.to_datetime(start)) &
              (df["Date"] <= pd.to_datetime(end))]

    # ------------------ TABLE ------------------
    st.subheader("📋 Entries")

    show = df_f[["Entry", "Date", "KM", "Liters", "Total Bill", "Avg", "₹/KM"]]
    st.dataframe(show, width="stretch")

    # ------------------ EDIT DELETE ------------------
    st.subheader("⚙️ Manage")

    idx = st.selectbox("Select Entry", df.index)
    row = df.loc[idx]

    new_date = st.date_input("Edit Date", row["Date"])
    new_km = st.number_input("Edit KM", value=float(row["KM"]))
    new_liters = st.number_input("Edit Liters", value=float(row["Liters"]))
    new_amt = st.number_input("Edit ₹", value=float(row["Total Bill"]))

    col1, col2 = st.columns(2)

    if col1.button("Update"):
        df.loc[idx, ["Date", "KM", "Liters", "Total Bill"]] = [
            str(new_date), new_km, new_liters, new_amt
        ]
        st.success("Updated")

    if col2.button("Delete"):
        df = df.drop(idx).reset_index(drop=True)
        st.warning("Deleted")

    # ------------------ GRAPH ------------------
    st.subheader("📈 Monthly Trend")

    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    monthly = df.groupby("Month")["Avg"].mean()

    st.line_chart(monthly)

    # ------------------ DOWNLOAD ------------------
    st.subheader("💾 Save")

    st.warning("⚠️ Download file after changes!")

    csv = df[["Date", "KM", "Liters", "Total Bill"]].to_csv(index=False)

    st.download_button("Download CSV", csv, "fuel_data.csv")