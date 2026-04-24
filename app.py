import streamlit as st
import pandas as pd
from openai import OpenAI
import tempfile
import os

st.set_page_config(page_title="StayVista Multi-Acquisition", page_icon="🏠", layout="wide")

# --- INITIALIZE SESSION STATE ---
# This keeps your data alive while you upload multiple videos
if 'master_data' not in st.session_state:
    st.session_state.master_data = pd.DataFrame(
        columns=["Villa Name", "Location", "BHK", "USP", "Expected Rent", "Manager Name", "Summary"]
    )

st.title("🏠 StayVista Acquisition: Bulk Processor")
st.markdown("Upload videos one by one. The table below will collect all data into a single file.")

# --- SIDEBAR ---
with st.sidebar:
    api_key = st.text_input("OpenAI API Key", type="password")
    if st.button("Clear All Data"):
        st.session_state.master_data = pd.DataFrame(columns=st.session_state.master_data.columns)
        st.rerun()

# --- UPLOAD SECTION ---
uploaded_file = st.file_uploader("Upload Villa Walkthrough", type=["mp4", "mov", "avi"])

if uploaded_file and api_key:
    client = OpenAI(api_key=api_key)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(uploaded_file.read())
        video_path = tmp_file.name

    if st.button("➕ Add to Master List"):
        with st.status("Processing Video...", expanded=True) as status:
            st.write("Transcribing audio...")
            with open(video_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file).text
            
            st.write("Extracting details...")
            prompt = f"Extract details from this StayVista villa transcript: '{transcript}'. Return format: Villa Name|Location|BHK|USP|Expected Rent|Manager Name|3-sentence Summary"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse and Append
            data_row = response.choices[0].message.content.strip().split("|")
            
            # Add to the Session State DataFrame
            new_entry = pd.DataFrame([data_row], columns=st.session_state.master_data.columns)
            st.session_state.master_data = pd.concat([st.session_state.master_data, new_entry], ignore_index=True)
            
            status.update(label="Villa Added Successfully!", state="complete")
        
        os.remove(video_path)

# --- DISPLAY MASTER LIST ---
st.divider()
st.subheader("📋 Master Acquisition List")

if not st.session_state.master_data.empty:
    # Display the table
    st.dataframe(st.session_state.master_data, use_container_width=True)

    # Download Button for the entire accumulated file
    csv = st.session_state.master_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Master CSV (All Villas)",
        data=csv,
        file_name="stayvista_acquisition_batch.csv",
        mime="text/csv",
        type="primary"
    )
else:
    st.info("No villas added yet. Upload a video above to start the list.")
