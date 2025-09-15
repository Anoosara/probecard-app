import streamlit as st
import pandas as pd
import io
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import datetime

# Step 1: ตั้งค่าหน้า Streamlit (page config + title)
st.set_page_config(page_title="Analyzer ", layout="wide")
st.title("📊 Probe Card Analyzer")

# Step 2: ตรวจสอบว่ามีไฟล์จากหน้า Home (multi_files_df) หรือไม่
# ถ้าไม่มี ให้แสดงคำเตือน
# ✅ ต้องมีไฟล์ก่อนถึงจะทำการวิเคราะห์ได้
if "multi_files_df" not in st.session_state or not st.session_state["multi_files_df"]:
    st.warning("⚠️ Please upload the file first.")
else:
    # Step 3: โหลด dict ของไฟล์และสร้าง tab สำหรับแต่ละไฟล์
    file_dict = st.session_state["multi_files_df"]
    tabs = st.tabs(list(file_dict.keys()))

    # Step 4: วนลูปวิเคราะห์แต่ละไฟล์ (แต่ละ tab)
    for tab, filename in zip(tabs, file_dict):
        with tab:
            st.subheader(f"📁 File: {filename}")
            df = file_dict[filename]

            # Step 5: ปุ่มลบไฟล์จาก session_state (ลบเฉพาะไฟล์นี้)
            if st.button(f"🗑️ Delete `{filename}`", key=f"remove_{filename}"):
                del st.session_state["multi_files_df"][filename]
                st.rerun()

            # Step 6: แสดงข้อมูลดิบให้ผู้ใช้ดู
            st.dataframe(df)

            # Step 7: ตรวจสอบว่าไฟล์เป็น Contact Resistance type หรือ Diameter/Planarity type
            contact_cols = next((col for col in df.columns if "Contact Resistance" in col), None)

            # Step 8: Branch สำหรับ Contact Resistance
            if contact_cols:
                # 8.1: แปลง Probe ID และคอลัมน์ contact ให้เป็นตัวเลข (ปลอดภัยต่อ errors)
                df['Probe ID'] = pd.to_numeric(df.get('Probe ID'), errors='coerce')
                df[contact_cols] = pd.to_numeric(df.get(contact_cols), errors='coerce')
                df = df.dropna(subset=['Probe ID', contact_cols])
                df_sorted = df.sort_values(by='Probe ID').reset_index(drop=True)

                # 8.2: สร้างกราฟ Contact Resistance vs Probe ID และแสดง
                fig_contact = px.scatter(df_sorted, x='Probe ID', y=contact_cols,
                                         title="Contact Resistance vs Probe ID")
                st.plotly_chart(fig_contact, use_container_width=True)

                # 8.3: ตรวจหา X/Y error ที่ออก spec และแสดงตาราง
                error_out = df_sorted[
                     (df_sorted['X Error (µm)'].abs() > 15) | (df_sorted['Y Error (µm)'].abs() > 15)
                        ]
                if not error_out.empty:
                   st.subheader("❗ Probe ID with X/Y Error Out of Spec (±15 µm)")
                   st.table(error_out[['Probe ID', 'Probe name', 'X Error (µm)', 'Y Error (µm)']])

                # 8.4: ตรวจ V-Align ถ้ามีคอลัมน์ และแสดงผล
                v_align_out = pd.DataFrame()
                if 'V Align (µm)' in df_sorted.columns:
                    v_align_out = df_sorted[df_sorted['V Align (µm)'] > 15]
                    if not v_align_out.empty:
                     st.subheader("❗ Probe ID with V-Align Out of Spec (> +15 µm)")
                     st.table(v_align_out[['Probe ID', 'Probe name', 'V Align (µm)']])

                # Step 9: บันทึกผลการวิเคราะห์ลง st.session_state["analyzed_files"] สำหรับกรณี Contact Resistance
                if "analyzed_files" not in st.session_state:
                   st.session_state["analyzed_files"] = {}

                st.session_state["analyzed_files"][filename] = {
                   "df_sorted": df_sorted,
                   "top5_max": pd.DataFrame(),
                   "top5_min": pd.DataFrame(),
                   "error_out": error_out,
                   "v_align_out": v_align_out,
                   "contact_cols": [contact_cols],
                    "planarity_out": pd.DataFrame(),
                   "filename": filename
                }

                # Step 10: ลิงก์ไปยังหน้า Download เพื่อดาวน์โหลดไฟล์ Excel ที่สร้าง
                st.page_link("pages/Download.py", label="📥 Go to Download Page", icon="📁")

            # Step 11: Branch สำหรับ Diameter / Planarity (non-contact files)
            else:
                # 11.1: แปลงคอลัมน์ที่ต้องการเป็นตัวเลข และ rename 'User Defined Label 4' เป็น 'Probe name' หากมี
                df['Probe ID'] = pd.to_numeric(df.get('Probe ID'), errors='coerce')
                df['Diameter (µm)'] = pd.to_numeric(df.get('Diameter (µm)'), errors='coerce')
                df['Planarity (µm)'] = pd.to_numeric(df.get('Planarity (µm)'), errors='coerce')
                df['X Error (µm)'] = pd.to_numeric(df.get('X Error (µm)'), errors='coerce')
                df['Y Error (µm)'] = pd.to_numeric(df.get('Y Error (µm)'), errors='coerce')
                if 'User Defined Label 4' in df.columns:
                   df = df.rename(columns={'User Defined Label 4': 'Probe name'})
                df = df.dropna(subset=['Probe ID'])
                df_sorted = df.sort_values(by='Probe ID').reset_index(drop=True)

                # Step 12: Diameter plot settings (UCL / LCL) — เก็บค่าใน session_state per-file
                st.markdown("### ⚙️ Diameter Reference Settings")
                ucl_key = f"ucl_{filename}"
                lcl_key = f"lcl_{filename}"
                if ucl_key not in st.session_state:
                 st.session_state[ucl_key] = 24.0
                if lcl_key not in st.session_state:
                  st.session_state[lcl_key] = 14.0

                st.session_state[ucl_key] = st.number_input(
                  "Enter UCL (Upper Control Limit)",
                   value=st.session_state[ucl_key],
                   step=0.5,
                    key=f"widget_{ucl_key}"
                      )

                st.session_state[lcl_key] = st.number_input(
                  "Enter LCL (Lower Control Limit)",
                 value=st.session_state[lcl_key],
                   step=0.5,
                   key=f"widget_{lcl_key}"
                   )

                # 12.1: วาดกราฟ Diameter และเพิ่มเส้น UCL/LCL
                ucl = st.session_state[ucl_key]
                lcl = st.session_state[lcl_key]
                fig_dia = px.scatter(df_sorted, x='Probe ID', y='Diameter (µm)', title="Diameter vs Probe ID")
                fig_dia.add_hline(y=ucl, line_color="red", annotation_text=f"UCL = {ucl}")
                fig_dia.add_hline(y=lcl, line_color="red", annotation_text=f"LCL = {lcl}")
                st.plotly_chart(fig_dia, use_container_width=True)

                # Step 13: คำนวณและแสดง Out of Spec สำหรับ Diameter
                out_of_spec = df_sorted[(df_sorted['Diameter (µm)'] > ucl) | (df_sorted['Diameter (µm)'] < lcl)]
                st.subheader(f"❗ Out of Spec Diameters ( < {lcl} or > {ucl} )")
                if out_of_spec.empty:
                 st.success("✅ All pins are within specification")
                else:
                 st.error(f"Find {len(out_of_spec)} pins out of range [{lcl}, {ucl}] µm")
                 st.table(out_of_spec[['Probe ID', 'Probe name', 'Diameter (µm)']])

                # Step 14: แสดง Top5 max / min Diameter
                top5_max = df_sorted.sort_values(by='Diameter (µm)', ascending=False).head(5)
                st.subheader("🔝 Top 5 Largest Diameters (All Pins)")
                st.table(top5_max[['Probe ID', 'Probe name', 'Diameter (µm)']])

                top5_min = df_sorted.sort_values(by='Diameter (µm)', ascending=True).head(5)
                st.subheader("🔻 Top 5 Smallest Diameters (All Pins)")
                st.table(top5_min[['Probe ID', 'Probe name', 'Diameter (µm)']])

                # Step 15: Planarity settings and checks (Delta 30 / ±15)
                st.markdown("### ⚙️ Planarity Reference Settings")
                planarity_mode = st.radio(
                "Choose Planarity Reference Type",
                ["Delta 30", "±15"],
                key=f"planarity_mode_{filename}"
                                     )
                fig_plan = px.scatter(df_sorted, x='Probe ID', y='Planarity (µm)', title="Planarity vs Probe ID")

                planarity_out = pd.DataFrame()
                if planarity_mode == "Delta 30":
                 max_val = df_sorted['Planarity (µm)'].max()
                 min_val = df_sorted['Planarity (µm)'].min()
                 delta = max_val - min_val
                 st.info(f"🔍 Delta = {delta:.2f} µm")
                 if delta <= 30:
                  st.success("✅ Within the specifications (Delta ≤ 30 µm)")
                 else:
                  st.error("❌ exceeds specifications (Delta > 30 µm)")
                  st.subheader("❗ Probe ID with Planarity Out of Spec (Delta > 30 µm)")
                  planarity_out = df_sorted.loc[
                   (df_sorted['Planarity (µm)'] == max_val) | (df_sorted['Planarity (µm)'] == min_val),
                   ['Probe ID', 'Probe name', 'Planarity (µm)']
                      ]
                  st.table(planarity_out)
                 fig_plan.add_hline(y=max_val, line_color="red", annotation_text=f"Max = {max_val:.2f}")
                 fig_plan.add_hline(y=min_val, line_color="red", annotation_text=f"Min = {min_val:.2f}")
                elif planarity_mode == "±15":
                  planarity_out = df_sorted[(df_sorted['Planarity (µm)'] > 15) | (df_sorted['Planarity (µm)'] < -15)]
                  st.info("🔍 Check that all values ​​must be within the range. [-15, +15] µm")
                  if planarity_out.empty:
                   st.success("✅ Within specifications (all within ±15 µm)")
                  else:
                   st.error("❌ Value exceeding ±15 µm")
                   st.subheader("❗ Probe ID with Planarity Out of Spec (±15 µm)")
                   st.table(planarity_out[['Probe ID', 'Probe name', 'Planarity (µm)']])
                  fig_plan.add_hline(y=15, line_color="red", annotation_text="+15 µm")
                  fig_plan.add_hline(y=-15, line_color="red", annotation_text="-15 µm")
                st.plotly_chart(fig_plan, use_container_width=True)

                # Step 16: X/Y error and V-Align checks for non-contact files
                error_out = df_sorted[
                    (df_sorted['X Error (µm)'].abs() > 15) | (df_sorted['Y Error (µm)'].abs() > 15)
                ]
                if not error_out.empty:
                    st.subheader("❗ Probe ID with X/Y Error Out of Spec (±15 µm)")
                    st.table(error_out[['Probe ID', 'Probe name', 'X Error (µm)', 'Y Error (µm)']])
                v_align_out = pd.DataFrame()
                if 'V Align (µm)' in df_sorted.columns:
                   v_align_out = df_sorted[df_sorted['V Align (µm)'] > 15]
                   if not v_align_out.empty:
                    st.subheader("❗ Probe ID with V-Align Out of Spec (> +15 µm)")
                    st.table(v_align_out[['Probe ID', 'Probe name', 'V Align (µm)']])

                # Step 17: บันทึกผลการวิเคราะห์ลง st.session_state["analyzed_files"] สำหรับ non-contact files
                if "analyzed_files" not in st.session_state:
                   st.session_state["analyzed_files"] = {}

                st.session_state["analyzed_files"][filename] = {
                    "df_sorted": df_sorted,
                    "top5_max": top5_max,
                    "top5_min": top5_min,
                    "error_out": error_out,
                    "v_align_out": v_align_out,
                    "out_of_spec" : out_of_spec,
                    "planarity_out": planarity_out,
                    "planarity_mode": planarity_mode,
                    "ucl": ucl,
                    "lcl": lcl,
                    "contact_cols":contact_cols,
                    "filename": filename
                    }

                # Step 18: ให้ลิงก์ไปหน้า Download เพื่อดาวน์โหลดไฟล์วิเคราะห์
                st.page_link("pages/Download.py", label="📥 Go to Download Page", icon="📁")
