import plotly.graph_objects as go
from streamlit_extras.metric_cards import style_metric_cards
import streamlit.components.v1 as components
import streamlit as st
import google.generativeai as genai
import os
import PyPDF2 as pdf
from dotenv import load_dotenv
import json
import re

# ---------------------- PAGE CONFIG ----------------------
st.set_page_config(page_title="Smart Resume Screener")

# ---------------------- CUSTOM STYLING ----------------------
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
        font-weight: bold;
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f8f9fa;
        text-align: center;
        padding: 10px 0;
        border-top: 1px solid #e6e6e6;
    }
    .social-links a {
        margin: 0 10px;
        color: #4CAF50;
        text-decoration: none;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------- CONFIGURATION ----------------------
load_dotenv()  # Load environment variables
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ---------------------- GEMINI FUNCTION ----------------------
def get_gemini_response(input_text):
    model = genai.GenerativeModel('gemini-pro-latest')
    response = model.generate_content(input_text)
    return response.text

# ---------------------- PDF EXTRACTION ----------------------
def input_pdf_text(uploaded_file):
    reader = pdf.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# ---------------------- PROMPT TEMPLATE ----------------------
input_prompt = """
Act as an expert ATS (Application Tracking System) with deep knowledge in tech fields including software engineering, data science, and data analysis. 

Your task is to analyze the following resume against the provided job description and provide a detailed assessment.

RESUME:
{text}

JOB DESCRIPTION:
{jd}

ANALYSIS REQUIREMENTS:
1. Calculate a match percentage based on skills, experience, and qualifications
2. List up to 5 key missing keywords from the job description that are not in the resume
3. Provide a detailed profile summary with specific recommendations

IMPORTANT: Your response MUST be a valid JSON object with the following structure:
{{
  "JD Match": "XX%",
  "MissingKeywords": ["keyword1", "keyword2", ...],
  "Profile Summary": "Detailed analysis and recommendations..."
}}

Guidelines for analysis:
- Be specific and actionable in your feedback
- Focus on both technical and soft skills
- Consider industry standards and best practices
- Provide constructive improvement suggestions
"""

# ---------------------- STREAMLIT UI ----------------------
st.title("Smart Resume Screener")
st.markdown("### Get instant feedback on your resume's ATS compatibility")

st.text("Improve Your Resume ATS")
jd = st.text_area("Paste the Job Description")
uploaded_file = st.file_uploader("Upload Your Resume", type="pdf", help="Please upload a PDF file")
submit = st.button("Submit")

# ---------------------- MAIN LOGIC ----------------------
if submit:
    if uploaded_file is not None:
        try:
            text = input_pdf_text(uploaded_file)
            response = get_gemini_response(input_prompt.format(text=text, jd=jd))

            # --- Clean and extract JSON from Gemini response ---
            response = response.strip()
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                response = json_match.group(0)

            # --- FIX JSON (auto-clean common issues) ---
            response = response.replace('\n', ' ')  # flatten newlines
            response = re.sub(r'(?<=,)\s*[a-zA-Z]\s*(?=\")', '', response)  # remove stray letters like 'g'
            response = re.sub(r'\\+', '\\\\', response)  # fix malformed backslashes

            # Parse JSON safely
            result = json.loads(response)

            # Display Results
            st.markdown("---")
            st.subheader("📊 ATS Score")

            match_percent = float(result["JD Match"].strip('%'))
            color = "#4CAF50" if match_percent >= 70 else "#FFC107" if match_percent >= 50 else "#F44336"
            st.markdown(
                f"<h2 style='text-align: center; color: {color};'>{result['JD Match']} Match</h2>",
                unsafe_allow_html=True
            )

            # Missing Keywords
            if result["MissingKeywords"]:
                st.subheader("🔍 Missing Keywords")
                cols = st.columns(3)
                for i, keyword in enumerate(result["MissingKeywords"]):
                    if keyword.strip():
                        cols[i % 3].error(f"• {keyword}")

            # Profile Summary
            st.subheader("📝 Profile Summary")
            st.info(result["Profile Summary"])

            # Raw JSON (for debugging)
            with st.expander("View Raw Analysis"):
                st.json(result)

            # Gauge Chart
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=match_percent,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "ATS Score", 'font': {'size': 24}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': 'red'},
                        {'range': [50, 70], 'color': 'orange'},
                        {'range': [70, 100], 'color': 'green'}
                    ],
                }
            ))
            st.plotly_chart(fig, use_container_width=True)

            # Footer
            st.markdown("""
            <div class='footer'>
                <p>Made with ❤️ by Divyanshu Kumar</p>
                <div class='social-links'>
                    <a href='https://github.com/geekdivyxnsh' target='_blank'>GitHub</a> | 
                    <a href='https://www.linkedin.com/in/k-divyanshu/' target='_blank'>LinkedIn</a> | 
                    <a href='https://leetcode.com/u/geekdivyxnsh/' target='_blank'>LeetCode</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        except json.JSONDecodeError as e:
            st.error("Error parsing the response. Here's the raw output:")
            st.text(response)
            st.error(f"JSON Parse Error: {str(e)}")

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

    else:
        st.warning("Please upload a resume before submitting.")
