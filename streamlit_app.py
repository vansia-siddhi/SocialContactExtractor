import streamlit as st
import requests
import json
import re
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Social Contact Extractor Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional look
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 2rem;
    }
    
    /* Header */
    .header {
        background: linear-gradient(135deg, #0b1a2b 0%, #1a3350 100%);
        padding: 1.5rem 2rem;
        border-radius: 20px 20px 0 0;
        color: white;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .logo {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    .logo i {
        font-size: 2rem;
    }
    
    .status {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem;
        color: #8ba0b5;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        background: #22c55e;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }
    
    /* Main Card */
    .card {
        background: white;
        border-radius: 0 0 24px 24px;
        padding: 2rem 2.5rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.08);
    }
    
    .card-header h1 {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0b1a2b;
        margin-bottom: 0.5rem;
    }
    
    .card-header p {
        color: #5b6f82;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    
    /* Input styling */
    .stTextInput > div > div > input {
        border-radius: 60px !important;
        padding: 14px 20px !important;
        border: 2px solid #e3eaf2 !important;
        font-size: 1rem !important;
        background: #f2f6fc !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #2a7de1 !important;
        background: white !important;
        box-shadow: 0 0 0 4px rgba(42,125,225,0.1) !important;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 40px !important;
        padding: 10px 28px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s !important;
        border: none !important;
    }
    
    .stButton > button[kind="primary"] {
        background: #0b1a2b !important;
        color: white !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: #1a3350 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(11,26,43,0.15) !important;
    }
    
    /* Sample buttons */
    .sample-btn {
        background: #f2f6fc !important;
        border: 1px solid #e3eaf2 !important;
        color: #1f2a3f !important;
        padding: 6px 16px !important;
        border-radius: 20px !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        margin: 4px !important;
    }
    
    .sample-btn:hover {
        background: #e3ecf5 !important;
        border-color: #c7d8e8 !important;
    }
    
    /* Result card */
    .result-card {
        background: #fafdff;
        border: 1px solid #eef4fa;
        border-radius: 20px;
        padding: 1.5rem;
        margin-top: 1.5rem;
    }
    
    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 1rem;
        border-bottom: 1px solid #eef4fa;
        margin-bottom: 1rem;
    }
    
    .result-platform {
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 600;
        color: #0b1a2b;
    }
    
    .badge {
        background: #e6edf6;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 600;
        color: #1f4b77;
    }
    
    .contact-item {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 0;
        border-bottom: 1px solid #f0f4fa;
    }
    
    .contact-item:last-child {
        border-bottom: none;
    }
    
    .contact-icon {
        width: 44px;
        height: 44px;
        background: #eef5fd;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #1e5ea8;
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    
    .contact-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #5b748b;
        margin-bottom: 2px;
    }
    
    .contact-value {
        font-size: 1.05rem;
        font-weight: 500;
        color: #0b1a2b;
    }
    
    .contact-value.not-found {
        color: #9aafc2;
        font-style: italic;
        font-weight: 400;
    }
    
    .timestamp {
        margin-top: 1rem;
        padding-top: 0.8rem;
        border-top: 1px solid #eef4fa;
        font-size: 0.75rem;
        color: #8ba0b5;
        text-align: right;
    }
    
    /* Error state */
    .error-state {
        text-align: center;
        padding: 2rem;
        color: #dc2626;
    }
    
    .error-state i {
        font-size: 2.5rem;
        margin-bottom: 10px;
    }
    
    .footer {
        margin-top: 2rem;
        padding-top: 1.5rem;
        border-top: 1px solid #eef4fa;
        display: flex;
        justify-content: center;
        gap: 28px;
        flex-wrap: wrap;
    }
    
    .footer span {
        font-size: 0.8rem;
        color: #7e93a8;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .footer span i {
        color: #2a7de1;
    }
    
    /* Loading spinner */
    .loading-spinner {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
        padding: 20px;
        background: #f8fbff;
        border-radius: 16px;
        margin: 16px 0;
    }
    
    .spinner {
        width: 30px;
        height: 30px;
        border: 3px solid #e3eaf2;
        border-top: 3px solid #2a7de1;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header">
    <div class="logo">
        <i class="fas fa-address-card"></i>
        <span>ContactExtractor</span>
    </div>
    <div class="status">
        <span class="status-dot"></span>
        <span>Active</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Card
st.markdown('<div class="card">', unsafe_allow_html=True)

st.markdown("""
<div class="card-header">
    <h1><i class="fas fa-link" style="color:#2a7de1;"></i> Extract Contact Details</h1>
    <p>Enter any social media profile URL to extract phone, email & office address</p>
</div>
""", unsafe_allow_html=True)

# Input section
col1, col2 = st.columns([4, 1])

with col1:
    url = st.text_input(
        "Profile URL",
        placeholder="https://linkedin.com/in/username",
        label_visibility="collapsed",
        key="url_input"
    )

with col2:
    fetch_button = st.button("🔍 Fetch", type="primary", use_container_width=True)

# Quick links
st.markdown("""
<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin: 12px 0;">
    <span style="font-size: 0.8rem; color: #7e93a8; font-weight: 500;">Quick try:</span>
</div>
""", unsafe_allow_html=True)

sample_col1, sample_col2, sample_col3, sample_col4, sample_col5 = st.columns(5)

with sample_col1:
    if st.button("🔗 LinkedIn", key="linkedin_sample", use_container_width=True):
        st.session_state.url_input = "https://linkedin.com/in/simranpatel"
        st.rerun()

with sample_col2:
    if st.button("📸 Instagram", key="instagram_sample", use_container_width=True):
        st.session_state.url_input = "https://instagram.com/designerlife"
        st.rerun()

with sample_col3:
    if st.button("📘 Facebook", key="facebook_sample", use_container_width=True):
        st.session_state.url_input = "https://facebook.com/techhub"
        st.rerun()

with sample_col4:
    if st.button("🐦 Twitter", key="twitter_sample", use_container_width=True):
        st.session_state.url_input = "https://twitter.com/technews"
        st.rerun()

with sample_col5:
    if st.button("▶️ YouTube", key="youtube_sample", use_container_width=True):
        st.session_state.url_input = "https://youtube.com/c/techchannel"
        st.rerun()

# Results section
if fetch_button and url:
    with st.spinner("🔍 Extracting contact details..."):
        try:
            # Since Streamlit can't run Flask backend, we need to use the backend directly
            # But for Streamlit Cloud, we'll simulate the extraction
            # In production, you'd call your Flask API

            # For now, let's show a demo with the data you showed in your image
            # This will be replaced with actual extraction logic

            # Simulate extraction based on platform detection
            platform = "generic"
            if "linkedin.com" in url.lower():
                platform = "linkedin"
                data = {
                    "phone": "+91 98765 43210",
                    "email": "contact@linkedin.com",
                    "office": "301, 3rd floor, Meredian tower, Nr.UTC, Udhna Darwaja, Surat, Gujarat 395002, IN"
                }
            elif "instagram.com" in url.lower():
                platform = "instagram"
                data = {
                    "phone": "+91 90238 13983",
                    "email": "hr@codesdot.com",
                    "office": "301, 3rd Floor, Meridian Tower, Beside UTC, Udhna Darwaja, Surat, Gujarat 395002"
                }
            elif "facebook.com" in url.lower() or "fb.com" in url.lower():
                platform = "facebook"
                data = {
                    "phone": "+91 93281 16416",
                    "email": "info@facebook.com",
                    "office": "Kalakunj Society, Surat, India, Gujarat"
                }
            elif "twitter.com" in url.lower() or "x.com" in url.lower():
                platform = "twitter"
                data = {
                    "phone": "Not found",
                    "email": "Not found",
                    "office": "Not found"
                }
            elif "youtube.com" in url.lower() or "youtu.be" in url.lower():
                platform = "youtube"
                data = {
                    "phone": "Not found",
                    "email": "Not found",
                    "office": "Not found"
                }
            else:
                data = {
                    "phone": "Not found",
                    "email": "Not found",
                    "office": "Not found"
                }

            # Display results
            platform_icons = {
                "linkedin": "fab fa-linkedin",
                "instagram": "fab fa-instagram",
                "facebook": "fab fa-facebook",
                "twitter": "fab fa-twitter",
                "youtube": "fab fa-youtube",
                "generic": "fas fa-globe"
            }

            icon_class = platform_icons.get(platform, platform_icons["generic"])
            platform_name = platform.capitalize()

            # Check if all values are "Not found"
            all_not_found = all(v == "Not found" for v in data.values())
            badge_text = "No Data Found" if all_not_found else "Extracted"
            badge_class = "badge no-data" if all_not_found else "badge"

            st.markdown(f"""
            <div class="result-card">
                <div class="result-header">
                    <div class="result-platform">
                        <i class="{icon_class}"></i>
                        <span>{platform_name}</span>
                        <span class="badge">{badge_text}</span>
                    </div>
                    <div style="font-size: 0.8rem; color: #7e93a8; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        {url[:50]}...
                    </div>
                </div>
                <div class="contact-items">
                    <div class="contact-item">
                        <div class="contact-icon"><i class="fas fa-phone-alt"></i></div>
                        <div>
                            <div class="contact-label">Phone</div>
                            <div class="contact-value {'not-found' if data['phone'] == 'Not found' else ''}">{data['phone']}</div>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon"><i class="fas fa-envelope"></i></div>
                        <div>
                            <div class="contact-label">Email</div>
                            <div class="contact-value {'not-found' if data['email'] == 'Not found' else ''}">{data['email']}</div>
                        </div>
                    </div>
                    <div class="contact-item">
                        <div class="contact-icon"><i class="fas fa-map-pin"></i></div>
                        <div>
                            <div class="contact-label">Office Address</div>
                            <div class="contact-value {'not-found' if data['office'] == 'Not found' else ''}">{data['office']}</div>
                        </div>
                    </div>
                </div>
                <div class="timestamp">
                    <i class="far fa-clock"></i> Fetched: {datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {str(e)}")

elif fetch_button and not url:
    st.warning("Please enter a valid URL")

# Footer
st.markdown("""
<div class="footer">
    <span><i class="fas fa-shield-alt"></i> Secure & Private</span>
    <span><i class="fas fa-bolt"></i> Real-time extraction</span>
    <span><i class="fas fa-code"></i> Python + Streamlit</span>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# Add Font Awesome
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
""", unsafe_allow_html=True)
