import streamlit as st
import pandas as pd
import io
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Analyzer ", layout="wide")
st.title("📊 Probe Card Analyzer")
#------------------------------------------------------------------------------------------------------#
# ✅ Dowload from muti_files
if "multi_files_df" not in st.session_state or not st.session_state["multi_files_df"]:
    st.warning("⚠️ Please upload the file first.")
else:
    file_dict = st.session_state["multi_files_df"]
    tabs = st.tabs(list(file_dict.keys()))
#-------------loop ananlysis for each file-----------------------------------------------------------------------------------------#
    for tab, filename in zip(tabs, file_dict):
        with tab:
            st.subheader(f"📁 File: {filename}")
            df = file_dict[filename]
#-----------delete file out of session---------------------------------------------------------------#
            if st.button(f"🗑️ Delete `{filename}`", key=f"remove_{filename}"):
                del st.session_state["multi_files_df"][filename]
                st.rerun()
#-----------show raw data----------------------------------------------------------------#
            st.dataframe(df)
#---Condition1:--fine Column Resistance-----------------------------------------------------------------------------#
            contact_cols = next((col for col in df.columns if "Contact Resistance" in col), None)
#-----------for ProbeID & Contact resistance--------------------------------------------------------------------#
            if contact_cols:
                # 🎯 Contact Resistance
                df['Probe ID'] = pd.to_numeric(df.get('Probe ID'), errors='coerce')
                df[contact_cols] = pd.to_numeric(df.get(contact_cols), errors='coerce')
                df = df.dropna(subset=['Probe ID', contact_cols])
                df_sorted = df.sort_values(by='Probe ID').reset_index(drop=True)

                fig_contact = px.scatter(df_sorted, x='Probe ID', y=contact_cols,
                                         title="Contact Resistance vs Probe ID")
                st.plotly_chart(fig_contact, use_container_width=True)
#------------------------Check X/Y Error Out of sprc---------------------------------------------------------------#
                error_out = df_sorted[
                     (df_sorted['X Error (µm)'].abs() > 15) | (df_sorted['Y Error (µm)'].abs() > 15)
                        ]
                if not error_out.empty:
                   st.subheader("❗ Probe ID with X/Y Error Out of Spec (±15 µm)")
                   st.table(error_out[['Probe ID', 'Probe name', 'X Error (µm)', 'Y Error (µm)']])

                # ❗ Check V-Align Out of Spec (> +15 µm)
                v_align_out = pd.DataFrame()
                if 'V Align (µm)' in df_sorted.columns:
                    v_align_out = df_sorted[df_sorted['V Align (µm)'] > 15]
                    if not v_align_out.empty:
                     st.subheader("❗ Probe ID with V-Align Out of Spec (> +15 µm)")
                     st.table(v_align_out[['Probe ID', 'Probe name', 'V Align (µm)']])
    # --------------------------------------------------------------------------------------------------------------#
# --------------------✅ บันทึกลง session_state สำหรับ Contact Resistance---------------------------------------------#
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
#------------------------ 🔗 ปุ่มลิงก์ไปหน้า Download.py-------------------------------------------------#
                st.page_link("pages/Download.py", label="📥 Go to Download(re) Page", icon="📁")
#----------------------------------------------------------------------------------------------------#                
            else:
                # 🎯 Convert & Clean
                df['Probe ID'] = pd.to_numeric(df.get('Probe ID'), errors='coerce')
                df['Diameter (µm)'] = pd.to_numeric(df.get('Diameter (µm)'), errors='coerce')
                df['Planarity (µm)'] = pd.to_numeric(df.get('Planarity (µm)'), errors='coerce')
                df['X Error (µm)'] = pd.to_numeric(df.get('X Error (µm)'), errors='coerce')
                df['Y Error (µm)'] = pd.to_numeric(df.get('Y Error (µm)'), errors='coerce')
                # ✅ Rename column ถ้ามี User Defined Label 4
                if 'User Defined Label 4' in df.columns:
                   df = df.rename(columns={'User Defined Label 4': 'Probe name'})
                df = df.dropna(subset=['Probe ID'])
                df_sorted = df.sort_values(by='Probe ID').reset_index(drop=True)

# ---------------------------------------------📈Plot Diameter--------------------------------------------#
                # 📌 Sidebar for choose Reference Lines
                st.markdown("### ⚙️ Diameter Reference Settings")
                
                # --- key สำหรับ widget ---
                ucl_key = f"ucl_{filename}"
                lcl_key = f"lcl_{filename}"

                # --- ค่า default ถ้ายังไม่เคยมี ---
                if ucl_key not in st.session_state:
                 st.session_state[ucl_key] = 24.0
                if lcl_key not in st.session_state:
                  st.session_state[lcl_key] = 14.0

                # --- สร้าง number_input เขียนค่า session_state โดยตรง ---
                st.session_state[ucl_key] = st.number_input(
                  "Enter UCL (Upper Control Limit)",
                   value=st.session_state[ucl_key],
                   step=0.5,
                    key=f"widget_{ucl_key}"   # ใช้ widget key แยกออกไป
                      )

                st.session_state[lcl_key] = st.number_input(
                  "Enter LCL (Lower Control Limit)",
                 value=st.session_state[lcl_key],
                   step=0.5,
                   key=f"widget_{lcl_key}"   # ใช้ widget key แยกออกไป
                   )

                # --- ดึงค่ามาใช้ plot ---
                ucl = st.session_state[ucl_key]
                lcl = st.session_state[lcl_key]
                # 📈 Plot Diameter
                fig_dia = px.scatter(
                df_sorted, 
                x='Probe ID', 
                y='Diameter (µm)', 
                title="Diameter vs Probe ID"
                                            )

                # Add lines UCL / LCL
                fig_dia.add_hline(y=ucl, line_color="red", annotation_text=f"UCL = {ucl}")
                fig_dia.add_hline(y=lcl, line_color="red", annotation_text=f"LCL = {lcl}")

                # Show graphs
                st.plotly_chart(fig_dia, use_container_width=True)

## ---------------------------------------------- 📈Out of Spec Table ------------------------------------------------------ #
                # หา Probe ที่ Diameter อยู่นอกช่วง [LCL, UCL]
                out_of_spec = df_sorted[
                (df_sorted['Diameter (µm)'] > ucl) | (df_sorted['Diameter (µm)'] < lcl)
                  ]

                st.subheader(f"❗ Out of Spec Diameters ( < {lcl} or > {ucl} )")
                if out_of_spec.empty:
                 st.success("✅ All pins are within specification")
                else:
                 st.error(f"Find {len(out_of_spec)} pins out of range [{lcl}, {ucl}] µm")
                 st.table(out_of_spec[['Probe ID', 'Probe name', 'Diameter (µm)']])              
    #-----------------------------------------------------------------------------------------------------#
                # 🔝 Top 5 Largest Diameters (all 400 pins)
                top5_max = df_sorted.sort_values(by='Diameter (µm)', ascending=False).head(5)
                st.subheader("🔝 Top 5 Largest Diameters (All Pins)")
                st.table(top5_max[['Probe ID', 'Probe name', 'Diameter (µm)']])

                # 🔻 Top 5 Smallest Diameters (all 400 pins)
                top5_min = df_sorted.sort_values(by='Diameter (µm)', ascending=True).head(5)
                st.subheader("🔻 Top 5 Smallest Diameters (All Pins)")
                st.table(top5_min[['Probe ID', 'Probe name', 'Diameter (µm)']])
#------------------------------------------------------------------------------------------------------#

# ----------------------------------------------📈Plot Planarity-----------------------------------------# 
                st.markdown("### ⚙️ Planarity Reference Settings")

                planarity_mode = st.radio(
                "Choose Planarity Reference Type",
                ["Delta 30", "±15"],
                key=f"planarity_mode_{filename}"  # key for device each file
                                     )

                # Plot Graphs Planarity
                fig_plan = px.scatter(df_sorted, x='Probe ID', y='Planarity (µm)', title="Planarity vs Probe ID")
#--------------------------------- Delta 30 --------------------------------------------------------------#
                planarity_out = pd.DataFrame()
                if planarity_mode == "Delta 30":
                # Calculation  Delta value  (max - min)
                 max_val = df_sorted['Planarity (µm)'].max()
                 min_val = df_sorted['Planarity (µm)'].min()
                 delta = max_val - min_val

                 st.info(f"🔍 Delta = {delta:.2f} µm")
                 if delta <= 30:
                  st.success("✅ Within the specifications (Delta ≤ 30 µm)")
                 else:
                  st.error("❌ exceeds specifications (Delta > 30 µm)")
                  st.subheader("❗ Probe ID with Planarity Out of Spec (Delta > 30 µm)")
                  # Choose row max / min 
                  planarity_out = df_sorted.loc[
                   (df_sorted['Planarity (µm)'] == max_val) | (df_sorted['Planarity (µm)'] == min_val),
                   ['Probe ID', 'Probe name', 'Planarity (µm)']
                      ]
                  st.table(planarity_out)
                 fig_plan.add_hline(y=max_val, line_color="red", annotation_text=f"Max = {max_val:.2f}")
                 fig_plan.add_hline(y=min_val, line_color="red", annotation_text=f"Min = {min_val:.2f}")
#------------------------------------------------±15 -----------------------------------------------------------------------#
                elif planarity_mode == "±15":
                # Check value [-15, +15]
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
                 # Show Graphs
                st.plotly_chart(fig_plan, use_container_width=True)

                # ❗ X/Y Error Out of Spec
                error_out = df_sorted[
                    (df_sorted['X Error (µm)'].abs() > 15) | (df_sorted['Y Error (µm)'].abs() > 15)
                ]
                if not error_out.empty:
                    st.subheader("❗ Probe ID with X/Y Error Out of Spec (±15 µm)")
                    st.table(error_out[['Probe ID', 'Probe name', 'X Error (µm)', 'Y Error (µm)']])
                # ❗ V Align Error Out of Spec
                if 'V Align (µm)' in df_sorted.columns:
                   v_align_out = df_sorted[df_sorted['V Align (µm)'] > 15]
                   if not v_align_out.empty:
                    st.subheader("❗ Probe ID with V-Align Out of Spec (> +15 µm)")
                    st.table(v_align_out[['Probe ID', 'Probe name', 'V Align (µm)']])
#--------------------------------------------------------------------------------------------------------#    
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
                    "planarity_mode": planarity_mode,  # <--- เพิ่มเก็บ planarity_out
                    "ucl": ucl,
                    "lcl": lcl,
                    "contact_cols":contact_cols,
                    "filename": filename
                    }
                # 🔗 ปุ่มไปหน้า Download
                # 🔗 ปุ่มลิงก์ไปหน้า Download.py
                st.page_link("pages/Download.py", label="📥 Go to Download(re) Page", icon="📁")
