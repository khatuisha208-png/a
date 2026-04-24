import streamlit as st
import pandas as pd
from openai import OpenAI
import tempfile
import os

st.set_page_config(page_title="StayVista Acquisition Portal", page_icon="🏡", layout="wide")

# --- INITIALIZE SESSION STATE ---
if 'master_data' not in st.session_state:
    st.session_state.master_data = pd.DataFrame(
        columns=["Villa Name", "Location", "BHK", "USP", "Expected Rent", "Manager Name", "Summary"]
    )

st.title("🏡 StayVista Acquisition: Multi-Format Processor")
st.markdown("Upload **Video walkthroughs** or **Audio recordings**. Data will be aggregated into the table below.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    st.divider()
    if st.button("🗑️ Clear Master List"):
        st.session_state.master_data = pd.DataFrame(columns=st.session_state.master_data.columns)
        st.rerun()

# --- UPLOAD SECTION ---
# Added support for audio formats (mp3, wav, m4a)
uploaded_file = st.file_uploader(
    "Upload Villa Walkthrough (Video or Audio)", 
    type=["mp4", "mov", "avi", "mp3", "wav", "m4a"]
)

if uploaded_file and api_key:
    client = OpenAI(api_key=api_key)
    
    # Get the file extension to handle temp file creation properly
    file_extension = os.path.splitext(uploaded_file.name)[1]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.read())
        temp_file_path = tmp_file.name

    if st.button("➕ Process & Add to List"):
        with st.status("Analyzing Media...", expanded=True) as status:
            try:
                # 1. Transcription (Whisper handles both audio and video natively)
                st.write("🎤 Transcribing...")
                with open(temp_file_path, "rb") as media_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=media_file
                    ).text
                
                # 2. Structured Extraction
                st.write("🤖 Extracting Villa details...")
                prompt = f"""
                Analyze this StayVista acquisition transcript: "{transcript}"
                Extract: Villa Name, Location, BHK, USP, Expected Rent, Manager Name.
                Also provide a 2-sentence summary.
                
                Return exactly in this format:
                NAME|LOCATION|BHK|USP|RENT|MANAGER|SUMMARY
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # 3. Parse and Append
                raw_data = response.choices[0].message.content.strip()
                data_row = raw_data.split("|")
                
                # Ensure the row matches the column length
                if len(data_row) == 7:
                    new_entry = pd.DataFrame([data_row], columns=st.session_state.master_data.columns)
                    st.session_state.master_data = pd.concat([st.session_state.master_data, new_entry], ignore_index=True)
                    status.update(label="✅ Added successfully!", state="complete")
                else:
                    st.error("AI output format error. Please try again.")
                    
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                os.remove(temp_file_path)

# --- DISPLAY & EXPORT ---
st.divider()
st.subheader("📋 Accumulated Acquisition Data")

if not st.session_state.master_data.empty:
    # Interactive Table
    st.dataframe(st.session_state.master_data, use_container_width=True)

    # Multi-format export
    col1, col2 = st.columns(2)
    
    csv = st.session_state.master_data.to_csv(index=False).encode('utf-8')
    
    col1.download_button(
        label="📥 Download Master CSV",
        data=csv,
        file_name="stayvista_master_list.csv",
        mime="text/csv",
        type="primary"
    )
    
    col2.info(f"Total Villas Processed: {len(st.session_state.master_data)}")
else:
    st.info("The list is currently empty. Upload media to begin.")
