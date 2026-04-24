import streamlit as st
import pandas as pd
import google.generativeai as genai
import tempfile
import os
import time

st.set_page_config(page_title="StayVista Free Acquisition Tool", page_icon="🏡", layout="wide")

# --- INITIALIZE SESSION STATE ---
if 'master_data' not in st.session_state:
    st.session_state.master_data = pd.DataFrame(
        columns=["Villa Name", "Location", "BHK", "USP", "Expected Rent", "Manager Name", "Summary"]
    )

st.title("🏡 StayVista Acquisition (Free Tier)")
st.markdown("Powered by Google Gemini. Upload video or audio for free extraction.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Setup")
    # Get your free key at https://aistudio.google.com/
    api_key = st.text_input("Enter Gemini API Key", type="password")
    if st.button("🗑️ Clear Master List"):
        st.session_state.master_data = pd.DataFrame(columns=st.session_state.master_data.columns)
        st.rerun()

# --- APP LOGIC ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    uploaded_file = st.file_uploader("Upload Walkthrough (Video/Audio)", type=["mp4", "mov", "mp3", "wav", "m4a"])

    if uploaded_file:
        if st.button("➕ Process Villa"):
            with st.status("Gemini is analyzing media...", expanded=True) as status:
                try:
                    # Save file locally
                    suffix = os.path.splitext(uploaded_file.name)[1]
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    # Upload to Google Flash Storage (Temporary)
                    st.write("📤 Uploading to Google AI Studio...")
                    gv_file = genai.upload_file(path=tmp_path)
                    
                    # Wait for processing
                    while gv_file.state.name == "PROCESSING":
                        time.sleep(2)
                        gv_file = genai.get_file(gv_file.name)

                    # Prompt for extraction
                    st.write("🧠 Extracting structured data...")
                    prompt = """
                    Act as a property acquisition manager. Extract the following details from this media:
                    Villa Name, Location, BHK, USP, Expected Rent, Manager Name.
                    Also provide a short summary.
                    
                    Return ONLY the values separated by a pipe (|) in this exact order:
                    Villa Name|Location|BHK|USP|Expected Rent|Manager Name|Summary
                    """
                    
                    response = model.generate_content([gv_file, prompt])
                    
                    # Parse output
                    data_row = response.text.strip().split("|")
                    
                    if len(data_row) >= 7:
                        new_entry = pd.DataFrame([data_row[:7]], columns=st.session_state.master_data.columns)
                        st.session_state.master_data = pd.concat([st.session_state.master_data, new_entry], ignore_index=True)
                        status.update(label="✅ Added to Master List!", state="complete")
                    else:
                        st.error("AI returned unexpected format. Try a clearer recording.")
                    
                    # Cleanup
                    genai.delete_file(gv_file.name)
                    os.remove(tmp_path)

                except Exception as e:
                    st.error(f"Error: {e}")

# --- DISPLAY TABLE ---
st.divider()
if not st.session_state.master_data.empty:
    st.dataframe(st.session_state.master_data, use_container_width=True)
    csv = st.session_state.master_data.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Master CSV", data=csv, file_name="stayvista_acquisition.csv", mime="text/csv")
else:
    st.info("Enter API Key and upload a file to begin.")
