import streamlit as st
import pandas as pd
import chardet
import io
from io import StringIO
from datetime import datetime
from datetime import datetime, time,timedelta

# Step 1: เวลาเซิร์ฟเวอร์ -> แปลงเป็นเวลาไทย (UTC+7) และตรวจสอบช่วงเวลาทำงาน
# ✅ ตรวจสอบเวลาเพื่อเปิด-ปิดแอป
# แก้ timezone เป็นเวลาประเทศไทย (UTC+7)
# ✅ เวลา UTC + แก้ timezone ให้เป็นเวลาประเทศไทย
utc_now = datetime.utcnow()
now_th = (utc_now + timedelta(hours=7)).time()
#------------------------------------------------------------------------------------------#
# Step 2: กำหนดช่วงเวลาอนุญาตให้ใช้งาน
# ✅ ช่วงเวลาอนุญาต
allowed_start = time(7, 0)
allowed_end = time(23, 59)
#-----------------------------------------------------------------------------------------#
# Step 3: ถ้าอยู่นอกเวลาทำงาน ให้แสดงข้อความและหยุดแอป
# ✅ ตรวจสอบเวลาและหยุดแอปหากนอกเวลา
if not (allowed_start <= now_th <= allowed_end):
    st.markdown("<h2 style='color:red;'>🚫 It is currently out of business hours.<br>(08:00–23:59)</h2>", unsafe_allow_html=True)
    st.stop()
#------------------------------------------------------------------------------------------#
# Step 4: ตั้งค่า layout ของหน้าและหัวเรื่อง
st.set_page_config(page_title="CSV → Excel Converter", layout="centered")
st.markdown(
    """
    <style>
    .main-title {
        font-size: 36px;
        font-weight: 800;
        color: #000000;
        margin-bottom: 10px;
    }
    .subtext {
        color: #222222;
        font-size: 16px;
        margin-top: -5px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)
st.write("⏰ Current time (TH):", now_th.strftime("%H:%M"))
st.markdown('<div class="main-title">📄 CSV → Excel (Filter by Probe ID)</div>', unsafe_allow_html=True)
st.markdown('<div class="subtext">Upload one or more CSV files to extract only the Probe ID section.</div>', unsafe_allow_html=True)
#------------------------------------------------------------------------------------------#
# Step 5: เตรียม session_state สำหรับเก็บ DataFrame หลายไฟล์
# ✅ Initialize session state for multiple files
if "multi_files_df" not in st.session_state:
    st.session_state.multi_files_df = {}
#------------------------------------------------------------------------------------------#
# Step 6: ปุ่มลบข้อมูลทั้งหมด (ถ้ามีไฟล์เก็บอยู่)
# ✅ ปุ่มลบข้อมูลทั้งหมด
if st.session_state.multi_files_df:
    if st.button("🗑️ Delete all uploaded data"):
        st.session_state.multi_files_df = {}
        st.rerun()
#------------------------------------------------------------------------------------------#
# Step 7: ตัวรับอัพโหลดไฟล์ CSV (หลายไฟล์ได้)
# 📤 Upload CSV(s)
uploaded_files = st.file_uploader("📂 Upload CSV file(s)", type=["csv"], accept_multiple_files=True)

# Step 8: ประมวลผลไฟล์ที่อัพโหลดทีละไฟล์
# - ตรวจจับ encoding ด้วย chardet
# - หา block ที่เริ่มด้วย "Probe ID"
# - อ่าน block เป็น DataFrame และแก้ชื่อคอลัมน์ (um/ตm -> µm)
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
# ------------------------------------------------------------------------------------------#
            # Step 9: เก็บ DataFrame ลง session_state (multi_files_df)
            # ✅ Save to session state dict
            st.session_state.multi_files_df[file_name] = df
#------------------------------------------------------------------------------------------#
# Step 10: แสดงไฟล์ที่เก็บไว้ และให้ดาวน์โหลดเป็น Excel แต่ละไฟล์ พร้อมปุ่มลบเฉพาะไฟล์
# ✅ Show stored data
if st.session_state.multi_files_df:
    st.subheader("📂 Stored Files")
    for fname, df in list(st.session_state.multi_files_df.items()):
        with st.expander(f"📄 {fname}"):
            st.dataframe(df)
#------------------------------------------------------------------------------------------#
            # Step 11: เตรียมไฟล์ Excel ในหน่วยความจำและปุ่มดาวน์โหลด
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
#------------------------------------------------------------------------------------------#
            # Step 12: ปุ่มลบไฟล์เฉพาะรายการ
            # ลบเฉพาะไฟล์
            if st.button(f"🗑️ Remove `{fname}`", key=f"remove_{fname}"):
                del st.session_state.multi_files_df[fname]
                st.rerun()
#------------------------------------------------------------------------------------------#
# Step 13: ลิงก์ไปยังหน้า Analyzer
# ➡️ ไปหน้า Analyzer 2
st.page_link("pages/Probe Card Analyzer.py", label="➡️ Go to 🔍 Probe Card Analyzer Page")
# ------------------------------------------------------------------------------------------#
# Step 14: ลิงก์ไปยังหน้า Merge & Replace
st.markdown("---")  # เส้นคั่น
st.markdown("## 🔗 Merge & Replace Tool")
st.markdown("Use this page to merge **Contact Resistance file** with **Diameter/Planarity file**.")
st.page_link("pages/MergeReplace.py", label="➡️ Go to 🔗 Merge & Replace Page")
