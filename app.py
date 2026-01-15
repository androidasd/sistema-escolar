import streamlit as st
import pandas as pd
from docx import Document
from github import Github, Auth
import io
import time
import json
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DA PÁGINA ---
ST_COR_PADRAO = "#00A8C6"
ST_TITULO_PADRAO = "SISTEMA ESCOLAR"

st.set_page_config(page_title=ST_TITULO_PADRAO, page_icon="🎓", layout="wide")

# --- CSS NUCLEAR (VISUAL LIMPO) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
        header { visibility: hidden !important; display: none !important; height: 0px !important; }
        [data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"] { display: none !important; }
        footer, #MainMenu, .viewerBadge_container__1QSob { display: none !important; }
        .block-container { padding-top: 0rem !important; margin-top: -4rem !important; padding-bottom: 2rem !important; }
        :root { --primary: #00A8C6; --card-bg: #ffffff; }
        .login-container {
            background: white; padding: 30px; border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #eee; margin-top: 60px;
        }
        div.stButton > button:first-child {
            background-color: var(--primary); color: white; border: none; border-radius: 8px; font-weight: 600;
        }
        div.stButton > button:first-child:hover { opacity: 0.9; }
        div[data-testid="metric-container"] {
            background-color: var(--card-bg); border-radius: 10px; padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid var(--primary); text-align: center;
        }
        .profile-popup-box {
            background-color: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15); color: #333; margin-top: 5px; font-size: 14px;
        }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

def enviar_email_boas_vindas(destinatario, nome_usuario):
    try:
        remetente = st.secrets["EMAIL_USER"]
        senha_app = st.secrets["EMAIL_PASSWORD"].replace(" ", "").strip()
        msg = MIMEMultipart()
        msg['From'] = remetente.strip()
        msg['To'] = destinatario
        msg['Subject'] = "Acesso Solicitado - Sistema Escolar"
        msg.attach(MIMEText(f"Olá {nome_usuario}, cadastro recebido. Aguarde aprovação.", 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente.strip(), senha_app)
