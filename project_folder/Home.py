import streamlit as st
import pandas as pd
import chardet
import io
from io import StringIO
from datetime import datetime

# 🌟 Page styling
st.set_page_config(page_title="CSV → Excel Converter", layout="centered")
st.markdown("""
    <style>
    .main-title {
        font-size: 36px;
        font-weight: 800;
        color: #F9FAFB;
        margin-bottom: 10px;
    }
    .subtext {
        color: #aaa;
        font-size: 16px;
        margin-top: -5px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📄 CSV → Excel (Probe Card Analyzer)</div>', unsafe_allow_html=True)
st.markdown('<div class="subtext">Upload one or more CSV files to extract only the Probe ID section.</div>', unsafe_allow_html=True)

# ✅ Initialize session state for multiple files
if "multi_files_df" not in st.session_state:
    st.session_state.multi_files_df = {}

# ✅ ปุ่มลบข้อมูลทั้งหมด
if st.session_state.multi_files_df:
    if st.button("🗑️ Delete all uploaded data"):
        st.session_state.multi_files_df = {}
        st.rerun()

# 📤 Upload CSV(s)
uploaded_files = st.file_uploader("📂 Upload CSV file(s)", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    for single_file in uploaded_files:
        file_name = single_file.name

        with st.spinner(f"⏳ Processing `{file_name}`..."):
            raw_bytes = single_file.read()
            detected_encoding = chardet.detect(raw_bytes)['encoding']
            text = raw_bytes.decode(detected_encoding or "utf-8", errors="ignore")
            lines = text.splitlines()

            # 🔍 Find the "Probe ID" row
            start_idx = None
            for i, line in enumerate(lines):
                first_col = line.strip().split(',')[0].strip()
                if first_col == "Probe ID":
                    start_idx = i
                    break

            if start_idx is None:
                st.error(f"❌ 'Probe ID' not found in `{file_name}`.")
                continue

            data_block = []
            for line in lines[start_idx:]:
                if line.strip() == "" or all(cell.strip() == "" for cell in line.strip().split(',')):
                    break
                data_block.append(line)

            csv_block = StringIO("\n".join(data_block))
            df = pd.read_csv(csv_block)
            df.columns = [col.replace("ตm", "µm").replace("um", "µm") for col in df.columns]

            # ✅ Save to session state dict
            st.session_state.multi_files_df[file_name] = df

# ✅ Show stored data
if st.session_state.multi_files_df:
    st.subheader("📂 Stored Files")
    for fname, df in list(st.session_state.multi_files_df.items()):
        with st.expander(f"📄 {fname}"):
            st.dataframe(df)

            # Download Excel
            towrite = io.BytesIO()
            df.to_excel(towrite, index=False, engine='openpyxl')
            towrite.seek(0)
            st.download_button(
                label=f"💾 Download Excel for {fname}",
                data=towrite,
                file_name=f"{fname.replace('.csv','')}_Filtered_ProbeID.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # ลบเฉพาะไฟล์
            if st.button(f"🗑️ Remove `{fname}`", key=f"remove_{fname}"):
                del st.session_state.multi_files_df[fname]
                st.rerun()

# ➡️ ไปหน้า Analyzer 2
st.page_link("pages/Probe Card Analyzer.py", label="➡️ Go to 🔍 Probe Card Analyzer ")
