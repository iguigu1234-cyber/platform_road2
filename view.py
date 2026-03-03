# =================================================================
# view.py - UIデザイン
# =================================================================
import streamlit as st

def apply_custom_style(config):
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
        html, body, [data-testid="stAppViewContainer"] {{
            font-family: 'Noto Sans JP', sans-serif !important;
            background-color: {config['bg_color']};
        }}
        .section-header {{
            background-color: {config['primary_color']};
            color: white;
            padding: 8px 15px;
            border-radius: 5px;
            margin: 20px 0 10px 0;
            font-weight: bold;
        }}
        .stButton>button {{ border-radius: 4px; font-weight: bold; }}
        </style>
    """, unsafe_allow_html=True)