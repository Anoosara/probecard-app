import streamlit as st
import pandas as pd
import chardet
from io import StringIO

st.set_page_config(page_title="🔗 Merge & Replace Tool", layout="wide")
st.title("🔗 Merge & Replace Tool")
st.markdown("Upload **2 files**: one from Diameter/Planarity and one from Contact Resistance.")
st.markdown(
    "<p style='color:gray;'>➡️ Left box = <span style='color:red; font-weight:bold;'>Diameter/Planarity</span>, "
    "Right box = <span style='color:red; font-weight:bold;'>Contact Resistance</span></p>",
    unsafe_allow_html=True
)

# ---------------------- Function: Clean CSV ---------------------- #
def clean_csv(uploaded_file):
    file_name = uploaded_file.name
    raw_bytes = uploaded_file.read()
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
        return None, file_name

    # Extract data block
    data_block = []
    for line in lines[start_idx:]:
        if line.strip() == "" or all(cell.strip() == "" for cell in line.strip().split(',')):
            break
        data_block.append(line)

    csv_block = StringIO("\n".join(data_block))
    df = pd.read_csv(csv_block)
    df.columns = [col.replace("ตm", "µm").replace("um", "µm") for col in df.columns]

    return df, file_name

# ---------------------- Upload Section ---------------------- #
st.subheader("📤 Upload Your Files")

col1, col2 = st.columns(2)

with col1:
    dp_file = st.file_uploader("Upload Diameter/Planarity file", type=["csv"], key="dp")

with col2:
    cres_file = st.file_uploader("Upload Contact Resistance file", type=["csv"], key="cres")

# ---------------------- Process Files ---------------------- #
if cres_file and dp_file:
    df_cres, name_cres = clean_csv(cres_file)
    df_dp, name_dp = clean_csv(dp_file)

    if df_cres is not None and df_dp is not None:
        st.success("✅ Both files cleaned successfully!")

        # 👉 Show side by side
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"📄 Cleaned Diameter/Planarity File: {name_dp}")
            st.dataframe(df_dp.head(20))
        with col2:
            st.subheader(f"📄 Cleaned Contact Resistance File: {name_cres}")
            st.dataframe(df_cres.head(20))

        # ---------------------- Merge & Replace ---------------------- #
        if st.button("🔗 Merge & Replace Now"):
            # Columns to replace from CRes
            replace_cols = ["X Error (µm)", "Y Error (µm)", "V Align (µm)"]

            # 🔍 Find special columns
            contact_col = next((col for col in df_cres.columns if col.startswith("Contact Resistance")), None)
            leakage_col = next((col for col in df_cres.columns if "Leakage" in col), None)

            merged_df = df_dp.copy()

            # 🔄 Replace X/Y/V Align
            for col in replace_cols:
                if col in df_cres.columns:
                    merged_df[col] = df_cres[col]

            # 🔄 Replace or Add Contact Resistance
            if contact_col:
                if contact_col in merged_df.columns:
                    merged_df[contact_col] = df_cres[contact_col]   # replace
                else:
                    merged_df[contact_col] = df_cres[contact_col]   # add

            # ➕ Always Add Leakage (new col only)
            if leakage_col in df_cres.columns:
                merged_df[leakage_col] = df_cres[leakage_col]

            # 📌 Reorder → move Contact Resistance & Leakage after Planarity
            if "Planarity (µm)" in merged_df.columns:
                planarity_idx = merged_df.columns.get_loc("Planarity (µm)")

                if contact_col and contact_col in merged_df.columns:
                    col_data = merged_df.pop(contact_col)
                    merged_df.insert(planarity_idx + 1, contact_col, col_data)
                    planarity_idx += 1

                if leakage_col in merged_df.columns:
                    col_data = merged_df.pop(leakage_col)
                    merged_df.insert(planarity_idx + 1, leakage_col, col_data)

            st.success("✅ Merge & Replace completed!")

            # Show merged preview
            st.subheader("📊 Merged File Preview")
            st.dataframe(merged_df.head(20))

            # Download merged file
            merged_file = StringIO()
            merged_df.to_csv(merged_file, index=False)
            st.download_button(
                label="💾 Download Merged CSV",
                data=merged_file.getvalue(),
                file_name="merged_output.csv",
                mime="text/csv"
            )
