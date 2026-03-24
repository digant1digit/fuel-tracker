import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# Excel
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference

# PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Fuel Tracker", layout="wide")

# ------------------ UI STYLE ------------------
st.markdown("""
<style>
.main {background-color: #0f172a; color: white;}
.stMetric {background-color: #1e293b; padding: 15px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

st.title("⛽ Fuel Tracker")

# ------------------ TEMPLATE ------------------
sample_df = pd.DataFrame([
    {"Date": "2026-03-01", "KM": 1000, "Liters": 3, "Total Bill": 300}
])

st.download_button("⬇️ Download Template",
                   sample_df.to_csv(index=False).encode("utf-8"),
                   "fuel_template.csv")

st.info("📌 Supports: 2026-03-01 OR 01-03-2026")

# ------------------ UPLOAD ------------------
uploaded_file = st.file_uploader("📂 Upload CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=None, engine="python")
else:
    df = pd.DataFrame(columns=["Date", "KM", "Liters", "Total Bill"])

# ------------------ VALIDATION ------------------
required = ["Date", "KM", "Liters", "Total Bill"]
if len(df) > 0 and not all(col in df.columns for col in required):
    st.error("❌ Invalid CSV format")
    st.stop()

# ------------------ CLEAN ------------------
if len(df) > 0:
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    for col in ["KM", "Liters", "Total Bill"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bad = df[df.isnull().any(axis=1)]
    if len(bad) > 0:
        st.warning("⚠️ Invalid rows removed")
        st.dataframe(bad, width="stretch")

    df = df.dropna()

# ------------------ ADD ------------------
with st.form("add"):
    c1, c2, c3, c4 = st.columns(4)
    date = c1.date_input("Date", datetime.today())
    km = c2.number_input("KM", min_value=0.0)
    liters = c3.number_input("Liters", min_value=0.0)
    amount = c4.number_input("₹", min_value=0.0)

    if st.form_submit_button("Add"):
        df = pd.concat([df, pd.DataFrame([{
            "Date": str(date),
            "KM": km,
            "Liters": liters,
            "Total Bill": amount
        }])], ignore_index=True)

# ------------------ CALCULATIONS ------------------
if len(df) > 0:
    df = df.sort_values("Date")

    df["Distance"] = df["KM"].diff()
    df["Avg"] = df["Distance"] / df["Liters"]
    df["₹/KM"] = df["Total Bill"] / df["Distance"]
    df["Entry"] = range(1, len(df) + 1)

    total_d = df["Distance"].sum()
    total_l = df["Liters"].sum()
    overall = total_d / total_l if total_l else 0

    c1, c2 = st.columns(2)
    c1.metric("Last Avg", f"{df.iloc[-1]['Avg']:.2f} km/l")
    c2.metric("Overall Avg", f"{overall:.2f} km/l")

    # FILTER
    s, e = st.columns(2)
    start = s.date_input("From", df["Date"].min())
    end = e.date_input("To", df["Date"].max())

    df_f = df[(df["Date"] >= pd.to_datetime(start)) &
              (df["Date"] <= pd.to_datetime(end))]

    # TABLE
    show = df_f[["Entry", "Date", "KM", "Liters", "Total Bill", "Avg", "₹/KM"]]
    st.dataframe(show, width="stretch")

    # EDIT
    idx = st.selectbox("Edit Entry", df.index)
    row = df.loc[idx]

    nd = st.date_input("Date", row["Date"])
    nk = st.number_input("KM", value=float(row["KM"]))
    nl = st.number_input("Liters", value=float(row["Liters"]))
    na = st.number_input("₹", value=float(row["Total Bill"]))

    if st.button("Update"):
        df.loc[idx] = [nd, nk, nl, na, None, None, None, idx+1]

    if st.button("Delete"):
        df = df.drop(idx).reset_index(drop=True)

    # GRAPH
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    st.line_chart(df.groupby("Month")["Avg"].mean())

    # ------------------ CSV EXPORT ------------------
    export = df.copy()
    export["Avg"] = export["Avg"].fillna(0).round(2)
    export["₹/KM"] = export["₹/KM"].fillna(0).round(2)

    st.download_button(
        "📥 CSV",
        export[["Date","KM","Liters","Total Bill","Avg","₹/KM"]].to_csv(index=False),
        "fuel.csv"
    )

    # ------------------ EXCEL EXPORT ------------------
    wb = Workbook()
    ws = wb.active

    headers = ["Date","KM","Liters","Total Bill","Avg","₹/KM"]
    ws.append(headers)

    for _, r in export.iterrows():
        ws.append([str(r["Date"]), r["KM"], r["Liters"], r["Total Bill"], r["Avg"], r["₹/KM"]])

    chart = LineChart()
    data = Reference(ws, min_col=5, min_row=1, max_row=ws.max_row)
    chart.add_data(data, titles_from_data=True)
    ws.add_chart(chart, "H2")

    buf = BytesIO()
    wb.save(buf)

    st.download_button("📊 Excel", buf.getvalue(), "report.xlsx")

    # ------------------ PDF EXPORT ------------------
    pdf_buf = BytesIO()
    doc = SimpleDocTemplate(pdf_buf)
    styles = getSampleStyleSheet()

    elements = [Paragraph("Fuel Report", styles["Title"])]

    table_data = [["Date","KM","Liters","Bill","Avg","₹/KM"]]
    for _, r in export.iterrows():
        table_data.append([str(r["Date"]), r["KM"], r["Liters"], r["Total Bill"], r["Avg"], r["₹/KM"]])

    table = Table(table_data)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.grey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("GRID",(0,0),(-1,-1),1,colors.black)
    ]))

    elements.append(table)
    doc.build(elements)

    st.download_button("📄 PDF", pdf_buf.getvalue(), "report.pdf")
