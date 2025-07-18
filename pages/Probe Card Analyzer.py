import streamlit as st
import pandas as pd
import io
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Analyzer 2", layout="wide")
st.title("📊 Probe Card Analyzer 2")

def save_table_as_image(df, title, filename):
    fig, ax = plt.subplots(figsize=(6, 2 + 0.3 * len(df)))
    fig.patch.set_visible(False)
    ax.axis('off')
    ax.axis('tight')
    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    plt.title(title, fontsize=12)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    st.download_button(
        label=f"📷 Download {filename}",
        data=buf.getvalue(),
        file_name=f"{filename}.png",
        mime="image/png"
    )
    buf.close()
    plt.close()

# ✅ โหลดจากหลายไฟล์
if "multi_files_df" not in st.session_state or not st.session_state["multi_files_df"]:
    st.warning("⚠️ Please upload the file first.")
else:
    file_dict = st.session_state["multi_files_df"]
    tabs = st.tabs(list(file_dict.keys()))

    for tab, filename in zip(tabs, file_dict):
        with tab:
            st.subheader(f"📁 File: {filename}")
            df = file_dict[filename]

            if st.button(f"🗑️ Delete `{filename}`", key=f"remove_{filename}"):
                del st.session_state["multi_files_df"][filename]
                st.rerun()

            st.dataframe(df)

            contact_cols = next((col for col in df.columns if "Contact Resistance" in col), None)

            if contact_cols:
                # 🎯 Contact Resistance
                df['Probe ID'] = pd.to_numeric(df.get('Probe ID'), errors='coerce')
                df[contact_cols] = pd.to_numeric(df.get(contact_cols), errors='coerce')
                df = df.dropna(subset=['Probe ID', contact_cols])
                df_sorted = df.sort_values(by='Probe ID').reset_index(drop=True)

                fig_contact = px.scatter(df_sorted, x='Probe ID', y=contact_cols,
                                         title="Contact Resistance vs Probe ID")
                st.plotly_chart(fig_contact, use_container_width=True)
                # ✅ บันทึกลง session_state สำหรับ Contact Resistance
                if "analyzed_files" not in st.session_state:
                   st.session_state["analyzed_files"] = {}

                st.session_state["analyzed_files"][filename] = {
                   "df_sorted": df_sorted,
                   "top5_max": pd.DataFrame(),
                   "top5_min": pd.DataFrame(),
                   "error_out": pd.DataFrame(),
                   "contact_cols": [contact_cols],
                   "filename": filename
}
                # 🔗 ปุ่มลิงก์ไปหน้า Download.py
                st.page_link("pages/Download.py", label="📥 Go to Download Page", icon="📁")
                
              

            else:
                # 🎯 Convert & Clean
                df['Probe ID'] = pd.to_numeric(df.get('Probe ID'), errors='coerce')
                df['Diameter (µm)'] = pd.to_numeric(df.get('Diameter (µm)'), errors='coerce')
                df['Planarity (µm)'] = pd.to_numeric(df.get('Planarity (µm)'), errors='coerce')
                df['X Error (µm)'] = pd.to_numeric(df.get('X Error (µm)'), errors='coerce')
                df['Y Error (µm)'] = pd.to_numeric(df.get('Y Error (µm)'), errors='coerce')
                df = df.dropna(subset=['Probe ID'])
                df_sorted = df.sort_values(by='Probe ID').reset_index(drop=True)

                # 📈 Diameter
                fig_dia = px.scatter(df_sorted, x='Probe ID', y='Diameter (µm)', title="Diameter vs Probe ID")
                fig_dia.add_hline(y=24, line_color="red", annotation_text="UCL = 24")
                fig_dia.add_hline(y=14, line_color="red", annotation_text="LCL = 14")
                st.plotly_chart(fig_dia, use_container_width=True)

                # 📈 Planarity
                fig_plan = px.scatter(df_sorted, x='Probe ID', y='Planarity (µm)', title="Planarity vs Probe ID")
                st.plotly_chart(fig_plan, use_container_width=True)

                # 🔝 Top 5 Largest Diameters
                top5_max = df_sorted.sort_values(by='Diameter (µm)', ascending=False).head(5)
                top5_max = top5_max.rename(columns={'User Defined Label 4': 'Probe name'})
                st.subheader("🔝 Top 5 Largest Diameters")
                st.table(top5_max[['Probe ID', 'Probe name', 'Diameter (µm)']])
                save_table_as_image(top5_max[['Probe ID', 'Probe name', 'Diameter (µm)']],
                                    "Top 5 Largest Diameters", f"top5_largest_{filename}")

                # 🔻 Top 5 Smallest Diameters
                top5_min = df_sorted.sort_values(by='Diameter (µm)', ascending=True).head(5)
                top5_min = top5_min.rename(columns={'User Defined Label 4': 'Probe name'})
                st.subheader("🔻 Top 5 Smallest Diameters")
                st.table(top5_min[['Probe ID', 'Probe name', 'Diameter (µm)']])
                save_table_as_image(top5_min[['Probe ID', 'Probe name', 'Diameter (µm)']],
                                    "Top 5 Smallest Diameters", f"top5_smallest_{filename}")

                # ❗ X/Y Error Out of Spec
                error_out = df_sorted[
                    (df_sorted['X Error (µm)'].abs() > 15) | (df_sorted['Y Error (µm)'].abs() > 15)
                ]
                if not error_out.empty:
                    st.subheader("❗ Probe ID with X/Y Error Out of Spec (±15 µm)")
                    st.table(error_out[['Probe ID', 'User Defined Label 4', 'X Error (µm)', 'Y Error (µm)']])
                    save_table_as_image(
                        error_out[['Probe ID', 'User Defined Label 4', 'X Error (µm)', 'Y Error (µm)']],
                        "XY Error Out of Spec", f"xy_error_out_of_spec_{filename}"
                    )

            

            
                if "analyzed_files" not in st.session_state:
                   st.session_state["analyzed_files"] = {}

                st.session_state["analyzed_files"][filename] = {
                    "df_sorted": df_sorted,
                    "top5_max": top5_max,
                    "top5_min": top5_min,
                    "error_out": error_out,
                    "contact_cols":contact_cols,
                    "filename": filename
                    }
                # 🔗 ปุ่มไปหน้า Download
                # 🔗 ปุ่มลิงก์ไปหน้า Download.py
                st.page_link("pages/Download.py", label="📥 Go to Download Page", icon="📁")
