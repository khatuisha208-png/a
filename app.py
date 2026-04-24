import streamlit as st
import pandas as pd
import whisper
import groq
import tempfile
import os
import json
import csv

# --- PAGE SETUP ---
st.set_page_config(page_title="StayVista Acquisition Portal", page_icon="🏡", layout="wide")

# --- INITIALIZE SESSION STATE ---
if 'master_df' not in st.session_state:
    st.session_state.master_df = pd.DataFrame()

# --- LOAD MODELS ---
@st.cache_resource
def load_whisper():
    return whisper.load_model("base")

whisper_model = load_whisper()

# --- GITHUB SECRETS / SIDEBAR ---
# On Streamlit Cloud, add GROQ_API_KEY to "Settings > Secrets"
api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("Groq API Key", type="password")

if not api_key:
    st.warning("Please add your Groq API Key to proceed.")
    st.stop()

groq_client = groq.Groq(api_key=api_key)

st.title("🏡 StayVista Villa Acquisition")
st.markdown("Upload walkthrough videos/audio to generate structured CSVs and summaries.")

# --- FILE UPLOADER ---
uploaded_file = st.file_uploader("Upload Video or Audio", type=["mp4", "mov", "m4a", "mp3", "wav"])

if uploaded_file:
    # Save file to temp
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    if st.button("🚀 Process Property"):
        with st.status("Processing...", expanded=True) as status:
            # 1. Transcribe
            st.write("🎤 Transcribing & Translating...")
            result = whisper_model.transcribe(tmp_path, task="translate")
            transcript = result["text"]
            
            # 2. Extract with Groq
            st.write("🤖 Extracting Data with Llama 3...")
            from prompts import SYSTEM_PROMPT # We will move your long prompt to a separate file
            
            chat_completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": st.secrets.get("SYSTEM_PROMPT")}, # Store prompt in secrets or a file
                    {"role": "user", "content": f"Transcription:\n\n{transcript}"}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            res_json = json.loads(chat_completion.choices[0].message.content)
            summary = res_json["summary"]
            csv_data = res_json["csv_data"]

            # 3. Add to Session Table
            new_row = pd.DataFrame([csv_data])
            st.session_state.master_df = pd.concat([st.session_state.master_df, new_row], ignore_index=True)
            
            status.update(label="✅ Processing Complete!", state="complete")

        # --- DISPLAY INDIVIDUAL RESULTS ---
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("📝 Property Summary")
            st.text_area("Summary Output", value=summary, height=300)
        with col2:
            st.subheader("📊 Extracted Data")
            st.write(csv_data)

    os.remove(tmp_path)

# --- MASTER TABLE & DOWNLOAD ---
st.divider()
if not st.session_state.master_df.empty:
    st.subheader("📋 Cumulative Acquisition List")
    st.dataframe(st.session_state.master_df)
    
    csv_bytes = st.session_state.master_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Master CSV File",
        data=csv_bytes,
        file_name="stayvista_acquisition_batch.csv",
        mime="text/csv"
    )
    if st.button("🗑️ Reset Table"):
        st.session_state.master_df = pd.DataFrame()
        st.rerun()
