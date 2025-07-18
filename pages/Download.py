import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
import tempfile
import os

st.set_page_config(page_title="📥 Download All", layout="wide")
st.title("📥 Download Analyzed Excel Files")

if "analyzed_files" not in st.session_state:
    st.session_state["analyzed_files"] = {}

if not st.session_state["analyzed_files"]:
    st.warning("⚠️ There is no analysis file. Please return to the Analyzer page.")
    st.stop()

if "download_files" not in st.session_state:
    st.session_state["download_files"] = {}

for i, (filename, data) in enumerate(st.session_state["analyzed_files"].items()):

    if st.button(f"🗑️ Delete `{filename}`", key=f"delete_{filename}"):
        del st.session_state["analyzed_files"][filename]
        if filename in st.session_state["download_files"]:
            del st.session_state["download_files"][filename]
        st.success(f"✅ Delete {filename} แล้ว")
        st.rerun()

    st.subheader(f"📁 {filename}")

    if filename in st.session_state["download_files"]:
        excel_data = st.session_state["download_files"][filename]
    else:
        df_sorted = data["df_sorted"]
        top5_max = data["top5_max"]
        top5_min = data["top5_min"]
        error_out = data["error_out"]
        contact_columns = data.get("contact_cols", [])

        tmpdir = tempfile.mkdtemp()

        # ✅ Graph & save as PNG
        if contact_columns:
            contact_data = df_sorted[["Probe ID"] + contact_columns].dropna()
            fig_contact = px.scatter(contact_data, x="Probe ID", y=contact_columns[0],
                                     title="Contact Resistance vs Probe ID")
            contact_path = os.path.join(tmpdir, f"contact_{i}.png")
            fig_contact.write_image(contact_path, scale=2)
        else:
            df_plot = df_sorted.dropna(subset=["Probe ID", "Diameter (µm)", "Planarity (µm)"])
            fig_dia = px.scatter(df_plot, x='Probe ID', y='Diameter (µm)', title="Diameter vs Probe ID")
            fig_dia.add_hline(y=24, line_color="red", annotation_text="UCL=24")
            fig_dia.add_hline(y=14, line_color="red", annotation_text="LCL=14")
            fig_pla = px.scatter(df_plot, x='Probe ID', y='Planarity (µm)', title="Planarity vs Probe ID")
            dia_path = os.path.join(tmpdir, f"dia_{i}.png")
            pla_path = os.path.join(tmpdir, f"pla_{i}.png")
            fig_dia.write_image(dia_path, scale=2)
            fig_pla.write_image(pla_path, scale=2)

        # ✅ Create Excel
        combined_excel = io.BytesIO()
        with pd.ExcelWriter(combined_excel, engine="xlsxwriter") as writer:
            df_sorted.to_excel(writer, sheet_name="All Data", index=False)

            if not contact_columns:
                top5_max.to_excel(writer, sheet_name="Top 5 Max Dia", index=False)
                top5_min.to_excel(writer, sheet_name="Top 5 Min Dia", index=False)

            if not error_out.empty:
                error_out[['Probe ID', 'User Defined Label 4', 'X Error (µm)', 'Y Error (µm)']].to_excel(
                    writer, sheet_name="XY Error", index=False)

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

        combined_excel.seek(0)
        st.session_state["download_files"][filename] = combined_excel.getvalue()
        excel_data = combined_excel.getvalue()

    st.download_button(
        label="📥 Download Excel + Graphs",
        data=excel_data,
        file_name=f"analyzed_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{filename}"
    )
    st.page_link("pages/Probe Card Analyzer.py", label="📥 Go to Probe Card Analyzer Page", icon="🔍")
