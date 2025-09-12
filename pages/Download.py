import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import tempfile
import os
#-----------------------Set name-----------------------------------#
st.set_page_config(page_title="📥 Download All", layout="wide")
st.title("📥 Download Analyzed Excel Files")
#-------------------Prepare session_state-----------------------------------#
if "analyzed_files" not in st.session_state:
    st.session_state["analyzed_files"] = {}

if not st.session_state["analyzed_files"]:
    st.warning("⚠️ There is no analysis file. Please return to the Analyzer page.")
    st.stop()
#----------------------store file-------------------------------------------#
if "download_files" not in st.session_state:
    st.session_state["download_files"] = {}

for i, (filename, data) in enumerate(st.session_state["analyzed_files"].items()):
#------------------------------Delete file-----------------------------------#
    if st.button(f"🗑️ Delete `{filename}`", key=f"delete_{filename}"):
        del st.session_state["analyzed_files"][filename]
        if filename in st.session_state["download_files"]:
            del st.session_state["download_files"][filename]
        st.success(f"✅ Delete {filename} แล้ว")
        st.rerun()

    st.subheader(f"📁 {filename}")
#------------------------------------------------------------------------------#
    if filename in st.session_state["download_files"]:
        excel_data = st.session_state["download_files"][filename]
    else:
        df_sorted = data["df_sorted"]
        top5_max = data["top5_max"]
        top5_min = data["top5_min"]
        error_out = data["error_out"]
        contact_columns = data.get("contact_cols", [])
        v_align_out = data.get("v_align_out", pd.DataFrame())
        planarity_out = data.get("planarity_out", pd.DataFrame())
        planarity_mode = data.get("planarity_mode", "Unknown")
        out_of_spec=data.get("out_of_spec",pd.DataFrame())
        ucl = st.session_state.get(f"ucl_{filename}", 24.0)
        lcl = st.session_state.get(f"lcl_{filename}", 14.0)    

        tmpdir = tempfile.mkdtemp()
#---------------------------------------------------------------------------------#
#------------------------------ ✅ Graph & save as PNG of CRES-----------------------------#
        if contact_columns:
            contact_data = df_sorted[["Probe ID"] + contact_columns].dropna()
            fig_contact = px.scatter(contact_data, x="Probe ID", y=contact_columns[0],
                                     title="Contact Resistance vs Probe ID")
            contact_path = os.path.join(tmpdir, f"contact_{i}.png")
            fig_contact.write_image(contact_path, scale=2)
#----------------------------- ✅ Graph & save as PNG of Dia,Pla--------------------#           
        else:
            df_plot = df_sorted.dropna(subset=["Probe ID", "Diameter (µm)", "Planarity (µm)"])
            fig_dia = px.scatter(df_plot, x='Probe ID', y='Diameter (µm)', title="Diameter vs Probe ID")
            fig_dia.add_hline(y=ucl, line_color="red", annotation_text=f"UCL={ucl}")
            fig_dia.add_hline(y=lcl, line_color="red", annotation_text=f"LCL={lcl}")
            fig_pla = px.scatter(df_plot, x='Probe ID', y='Planarity (µm)', title="Planarity vs Probe ID")
            if planarity_mode == "Delta 30" :
              max_val = df_sorted['Planarity (µm)'].max()
              min_val = df_sorted['Planarity (µm)'].min()
              fig_pla.add_hline(y=max_val, line_color="red", annotation_text=f"Max = {max_val:.2f}")
              fig_pla.add_hline(y=min_val, line_color="red", annotation_text=f"Min = {min_val:.2f}")
            elif planarity_mode == "±15":
              fig_pla.add_hline(y=15, line_color="red", annotation_text="+15 µm")
              fig_pla.add_hline(y=-15, line_color="red", annotation_text="-15 µm")
            dia_path = os.path.join(tmpdir, f"dia_{i}.png")
            pla_path = os.path.join(tmpdir, f"pla_{i}.png")
            fig_dia.write_image(dia_path, scale=2)
            fig_pla.write_image(pla_path, scale=2)

        # ✅ Create Excel
        combined_excel = io.BytesIO()
        with pd.ExcelWriter(combined_excel, engine="xlsxwriter") as writer:
            df_sorted.to_excel(writer, sheet_name="All Data", index=False)
        # wirte top5 max/min---------------------------------------------#
            if not contact_columns:
        # กรองข้อมูลให้อยู่ในช่วง UCL/LCL
              # 🔝 Top 5 Largest Diameters (All Pins)
              top5_max = df_sorted.sort_values(by='Diameter (µm)', ascending=False).head(5)
              top5_max.to_excel(writer, sheet_name="Top 5 Max Dia (All)", index=False)

             # 🔻 Top 5 Smallest Diameters (All Pins)
              top5_min = df_sorted.sort_values(by='Diameter (µm)', ascending=True).head(5)
              top5_min.to_excel(writer, sheet_name="Top 5 Min Dia (All)", index=False)
              if not out_of_spec.empty:
                    out_of_spec[['Probe ID', 'Probe name', 'Diameter (µm)']].to_excel(
                        writer,
                        sheet_name=f"Out of Spec Dia ({lcl}-{ucl})",
                        index=False
                    )
        #wite X/Y error ----------------------------------------------------------------#
            if not error_out.empty:
                error_out[['Probe ID', 'Probe name', 'X Error (µm)', 'Y Error (µm)']].to_excel(
                    writer, sheet_name="XY Error", index=False)
            if not v_align_out.empty:
                    v_align_out[['Probe ID', 'Probe name', 'V Align (µm)']].to_excel(
                     writer, sheet_name="V-Align Out", index=False)

            if not planarity_out.empty:
               sheet_name = f"Planarity Out ({planarity_mode})"
               planarity_out[['Probe ID', 'Probe name', 'Planarity (µm)']].to_excel(
               writer, sheet_name=sheet_name, index=False)
        # add pic------------------------------------------------------------------------#
            workbook = writer.book
            if contact_columns:
                contact_ws = workbook.add_worksheet("Contact Resistance Graph")
                writer.sheets["Contact Resistance Graph"] = contact_ws
                contact_ws.insert_image("B2", contact_path)
            else:
                dia_ws = workbook.add_worksheet("Diameter Graph")
                pla_ws = workbook.add_worksheet("Planarity Graph")
                writer.sheets["Diameter Graph"] = dia_ws
                writer.sheets["Planarity Graph"] = pla_ws
                dia_ws.insert_image("B2", dia_path)
                pla_ws.insert_image("B2", pla_path)
#----------------------------------------------------------------------------------------------#
        combined_excel.seek(0)
        st.session_state["download_files"][filename] = combined_excel.getvalue()
        excel_data = combined_excel.getvalue()
#----------------------------------------------------------------------------------------------#
    st.download_button(
        label="📥 Download Excel + Graphs",
        data=excel_data,
        file_name=f"analyzed_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{filename}"
    )
    st.page_link("pages/Probe Card Analyzer.py", label="📥 Go to Probe Card Analyzer Page", icon="🔍")
