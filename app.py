import streamlit as st
import requests
from PyPDF2 import PdfReader

# OCR
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

# YouTube
import yt_dlp
import re

# -------------------------------
# TESSERACT PATH
# -------------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(page_title="AI Notes Generator", layout="centered")

st.title("📚 AI Notes Generator")
st.markdown("Convert text, PDFs, or YouTube videos into structured notes 🚀")

# -------------------------------
# INPUT TYPE
# -------------------------------
option = st.radio("Choose input type:", ["Text", "PDF", "YouTube"])

text_data = ""

# -------------------------------
# TEXT INPUT
# -------------------------------
if option == "Text":
    text_data = st.text_area("Enter your text here:")

# -------------------------------
# PDF INPUT (OCR FIXED)
# -------------------------------
elif option == "PDF":
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")

    if uploaded_file:
        reader = PdfReader(uploaded_file)
        text_list = []

        # Normal extraction
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text_list.append(content)

        text_data = " ".join(text_list)

        # OCR fallback
        if not text_data.strip():
            st.warning("⚠️ Using OCR for scanned PDF...")

            images = convert_from_bytes(uploaded_file.read())
            ocr_text = ""

            for img in images:
                ocr_text += pytesseract.image_to_string(img)

            text_data = ocr_text

        if not text_data.strip():
            st.error("❌ Could not extract text from this PDF")

# -------------------------------
# YOUTUBE INPUT (FIXED + CLEAN)
# -------------------------------
elif option == "YouTube":

    video_url = st.text_input("Enter YouTube URL")

    def get_transcript(url):
        try:
            ydl_opts = {
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],
                'skip_download': True,
                'quiet': True
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                subs = None

                if 'subtitles' in info and 'en' in info['subtitles']:
                    subs = info['subtitles']['en']
                elif 'automatic_captions' in info and 'en' in info['automatic_captions']:
                    subs = info['automatic_captions']['en']

                if subs:
                    sub_url = subs[0]['url']
                    response = requests.get(sub_url)

                    # CLEAN TEXT (remove XML tags)
                    data = response.text
                    clean_text = re.sub('<.*?>', '', data)

                    return clean_text

        except Exception as e:
            print(e)
            return ""

    if video_url:
        text_data = get_transcript(video_url)

        if not text_data.strip():
            st.error("❌ No captions available for this video")
            st.info("👉 Try another video (educational videos work best)")

# -------------------------------
# CHUNKING
# -------------------------------
def chunk_text(text, size=2000):
    return [text[i:i+size] for i in range(0, len(text), size)]

# -------------------------------
# LLM CALL
# -------------------------------
def generate_notes(text):
    chunks = chunk_text(text)
    final_output = ""

    progress = st.progress(0)

    for i, chunk in enumerate(chunks):
        prompt = f"""
        Summarize into structured notes:

        - Summary
        - Key Points
        - Important Concepts
        - 3 Questions with Answers

        Keep it short and clear.

        Text:
        {chunk}
        """

        try:
            res = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi3",
                    "prompt": prompt,
                    "stream": False
                }
            )

            result = res.json()

            if "response" in result:
                final_output += result["response"] + "\n\n"
            else:
                final_output += f"⚠️ Error: {result}\n\n"

        except Exception as e:
            final_output += f"⚠️ Exception: {str(e)}\n\n"

        progress.progress((i + 1) / len(chunks))

    return final_output

# -------------------------------
# BUTTON
# -------------------------------
if st.button("Generate Notes"):
    if not text_data.strip():
        st.warning("Please provide input")
    else:
        with st.spinner("Generating notes..."):
            output = generate_notes(text_data)

        st.subheader("📌 Generated Notes")
        st.write(output)

        st.download_button(
            label="Download Notes",
            data=output,
            file_name="notes.txt",
            mime="text/plain"
        )