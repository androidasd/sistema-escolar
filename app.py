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
        server.sendmail(remetente.strip(), destinatario, msg.as_string())
        server.quit()
        return True, "Enviado"
    except Exception as e: return False, str(e)

# --- CONEXÃO GITHUB INTELIGENTE ---
BRANCH_ATUAL = "main" # Valor padrão inicial
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    auth = Auth.Token(TOKEN)
    g = Github(auth=auth)
    user = g.get_user()
    
    # 1. Tenta pegar o repositório pelo nome exato
    NOME_REPO = "sistema-escolar"
    try:
        repo_ref = user.get_repo(NOME_REPO)
    except:
        # Se falhar, tenta achar na lista
        repo_ref = None
        for r in user.get_repos():
            if "sistema" in r.name.lower():
                repo_ref = r
                break
    
    if not repo_ref:
        st.error(f"❌ Repositório '{NOME_REPO}' não encontrado.")
        st.stop()
        
    # 2. DETECÇÃO AUTOMÁTICA DA BRANCH (MAIN vs PRINCIPAL vs MASTER)
    BRANCH_ATUAL = repo_ref.default_branch

except Exception as e:
    st.error(f"Erro Github: {e}")
    st.stop()

# --- ARQUIVOS (NOMES EXATOS DA IMAGEM) ---
ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUSÕES- PA-RESSACA.docx'
ARQ_USERS = 'usuários.json'
ARQ_CONFIG = 'config.json'

# --- OPERAÇÕES DE ARQUIVO ---
def carregar_json(arquivo):
    try:
        content = repo_ref.get_contents(arquivo, ref=BRANCH_ATUAL)
        return json.loads(content.decoded_content.decode()), content.sha
    except: return {}, None

def salvar_json(arquivo, dados, sha, mensagem):
    try:
        dados_str = json.dumps(dados, indent=4)
        if sha: repo_ref.update_file(arquivo, mensagem, dados_str, sha, branch=BRANCH_ATUAL)
        else: repo_ref.create_file(arquivo, mensagem, dados_str, branch=BRANCH_ATUAL)
        return True
    except: return False

@st.cache_data(ttl=60)
def carregar_dados_word():
    def processar(nome_arq, categoria):
        local = []
        try:
            c = repo_ref.get_contents(nome_arq, ref=BRANCH_ATUAL)
            doc = Document(io.BytesIO(c.decoded_content))
            for tabela in doc.tables:
                for linha in tabela.rows:
                    if len(linha.cells) >= 2:
                        num = linha.cells[0].text.strip()
                        nome = linha.cells[1].text.strip().upper()
                        obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                        if len(nome) > 3 and "NOME" not in nome:
                            local.append({"Numero": num, "Nome": nome, "Categoria": categoria, "Obs": obs})
            return local
        except Exception as e:
            st.error(f"Erro lendo {nome_arq}: {e}")
            return []
    return processar(ARQ_PASSIVOS, "Passivo") + processar(ARQ_CONCLUINTES, "Concluinte")

def salvar_aluno_word(arquivo_nome, numero, nome, obs):
    try:
        c = repo_ref.get_contents(arquivo_nome, ref=BRANCH_ATUAL)
        doc = Document(io.BytesIO(c.decoded_content))
        if len(doc.tables) > 0:
            tab = doc.tables[0]
            row = tab.add_row()
            row.cells[0].text = numero
            row.cells[1].text = nome.upper()
            if len(row.cells) > 2: row.cells[2].text = obs
            buffer = io.BytesIO()
            doc.save(buffer)
            repo_ref.update_file(arquivo_nome, f"Add Aluno: {nome}", buffer.getvalue(), c.sha, branch=BRANCH_ATUAL)
            return True
    except: return False

config_data, config_sha = carregar_json(ARQ_CONFIG)
COR_TEMA = config_data.get("theme_color", ST_COR_PADRAO)
NOME_ESCOLA = config_data.get("school_name", ST_TITULO_PADRAO)
LOGO_URL = config_data.get("logo_url", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

# --- LOGIN ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None

if not st.session_state['user_info']:
    col_e, col_c, col_d = st.columns([5, 3, 5])
    with col_c:
        with st.container():
            st.markdown(f"""
            <div class="login-container" style="text-align:center;">
                <img src="{LOGO_URL}" width="70" style="margin-bottom:10px;">
                <h3 style="color:{COR_TEMA}; margin:0; font-weight:700;">{NOME_ESCOLA}</h3>
                <p style="color:gray; font-size:12px;">Gestão Acadêmica</p>
                <hr style="opacity:0.2; margin: 15px 0;">
                <small style="color:#ddd; font-size:10px;">Branch: {BRANCH_ATUAL}</small>
            </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["ENTRAR", "CADASTRAR"])
            with tab1:
                with st.form("login_frm"):
                    email = st.text_input("E-mail")
                    senha = st.text_input("Senha", type="password")
                    if st.form_submit_button("ACESSAR", use_container_width=True):
                        try: s_adm = st.secrets["SENHA_SISTEMA"]
                        except: s_adm = "admin"
                        if email.lower() == "admin@gmail.com" and senha == s_adm:
                            st.session_state['user_info'] = {"username": "Admin", "name": "Administrador Principal", "role": "admin", "email": "admin@gmail.com", "unit": "DIRETORIA"}
                            st.rerun()
                        db, _ = carregar_json(ARQ_USERS)
                        u = next((x for x in db.get("users", []) if x.get('email', '').lower() == email.lower() and x['password'] == hash_senha(senha)), None)
                        if u:
                            if u.get('status') == 'active': st.session_state['user_info'] = u; st.rerun()
                            else: st.warning("Cadastro em análise.")
                        else: st.error("Dados inválidos.")
            with tab2:
                with st.form("reg_frm"):
                    n = st.text_input("Nome"); e = st.text_input("E-mail"); s = st.text_input("Senha", type="password")
                    if st.form_submit_button("CRIAR CONTA", use_container_width=True):
                        if "@" not in e: st.error("E-mail inválido")
                        else:
                            db, sha = carregar_json(ARQ_USERS)
                            lst = db.get("users", [])
                            if any(x.get('email') == e for x in lst): st.error("E-mail já existe.")
                            else:
                                with st.spinner("Criando..."):
                                    lst.append({"username": e.split("@")[0], "password": hash_senha(s), "name": n, "email": e, "role": "user", "status": "pending", "unit": "Geral"})
                                    if not db: db = {"users": []}
                                    db['users'] = lst
                                    salvar_json(ARQ_USERS, db, sha, f"Reg {e}")
                                    enviar_email_boas_vindas(e, n)
                                    st.success("Solicitação enviada!")
    st.stop()

# --- ÁREA LOGADA ---
user = st.session_state['user_info']
with st.container():
    c_logo, c_user = st.columns([2, 3])
    with c_logo:
        st.markdown(f"""<div style="display:flex; align-items:center; gap:12px;"><img src="{LOGO_URL}" width="40"><div><h4 style="margin:0; color:{COR_TEMA}; font-weight:800;">{NOME_ESCOLA}</h4></div></div>""", unsafe_allow_html=True)
    with c_user:
        c_info, c_logout = st.columns([4, 1])
        with c_info:
            with st.expander(f"👤 {user['name'].split()[0]}", expanded=False):
                st.markdown(f"""<div class="profile-popup-box"><strong>{user['name']}</strong><br><small>{user.get('email')}</small><br><span style="color:{COR_TEMA}; font-weight:bold;">{user['role'].upper()}</span></div>""", unsafe_allow_html=True)
        with c_logout:
            if st.button("SAIR"): st.session_state['user_info'] = None; st.rerun()
st.divider()

opts = ["Dashboard", "Pesquisar", "Cadastrar Aluno"]
icons = ["house", "search", "person-plus"]
if user['role'] == 'admin': opts.append("Administração"); icons.append("gear")

selected = option_menu(menu_title=None, options=opts, icons=icons, default_index=0, orientation="horizontal", styles={"container": {"padding": "0!important", "background-color": "#ffffff"}, "icon": {"color": COR_TEMA}, "nav-link-selected": {"background-color": COR_TEMA, "color": "white"}})
st.write("")

if selected in ["Dashboard", "Pesquisar"]: df = pd.DataFrame(carregar_dados_word())

if selected == "Dashboard":
    st.subheader("📊 Visão Geral")
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(df)); col2.metric("Concluintes", len(df[df['Categoria']=="Concluinte"])); col3.metric("Passivos", len(df[df['Categoria']=="Passivo"]))
        st.write(""); st.markdown("##### 📌 Últimas Atualizações")
        st.dataframe(df.tail(8), use_container_width=True, hide_index=True)
    else: st.info("Sem dados (Tabelas vazias ou não encontradas).")

elif selected == "Pesquisar":
    st.subheader("🔍 Buscar Aluno")
    busca = st.text_input("Nome:", placeholder="Digite...")
    if busca and not df.empty:
        res = df[df['Nome'].str.contains(busca.upper(), na=False)]
        st.dataframe(res, use_container_width=True, hide_index=True)
    elif busca: st.warning("Não encontrado.")

elif selected == "Cadastrar Aluno":
    st.subheader("📝 Nova Matrícula")
    with st.container():
        with st.form("novo_aluno_form"):
            c1, c2 = st.columns([1, 4])
            num = c1.text_input("Nº")
            nome = c2.text_input("Nome")
            c3, c4 = st.columns(2)
            tipo = c3.radio("Situação", ["Passivos", "Concluintes"], horizontal=True)
            obs = c4.text_input("Obs")
            if st.form_submit_button("💾 SALVAR"):
                arq = ARQ_PASSIVOS if tipo == "Passivos" else ARQ_CONCLUINTES
                if not num: num = "S/N"
                if salvar_aluno_word(arq, num, nome, obs): st.toast("Salvo!", icon="✅"); time.sleep(1); st.cache_data.clear(); st.rerun()
                else: st.error("Erro.")

elif selected == "Administração":
    st.subheader("⚙️ Configurações")
    tab1, tab2, tab3 = st.tabs(["Usuários", "Senhas", "Sistema"])
    with tab1:
        db, sha = carregar_json(ARQ_USERS)
        if db.get("users"):
            df_u = pd.DataFrame(db['users'])
            edited = st.data_editor(df_u, key="editor_users", use_container_width=True, column_config={"status": st.column_config.SelectboxColumn("Acesso", options=["active", "pending"]), "role": st.column_config.SelectboxColumn("Nível", options=["user", "admin"])})
            if st.button("Salvar Acessos"):
                db['users'] = edited.to_dict('records')
                salvar_json(ARQ_USERS, db, sha, "Update Users"); st.success("Ok!"); time.sleep(1); st.rerun()
    with tab2:
        db, sha = carregar_json(ARQ_USERS)
        emails = [u['email'] for u in db.get("users", [])]
        sel = st.selectbox("Usuário:", emails)
        p1 = st.text_input("Nova Senha", type="password"); p2 = st.text_input("Repetir", type="password")
        if st.button("Trocar"):
            if p1 == p2:
                for u in db['users']: 
                    if u['email'] == sel: u['password'] = hash_senha(p1)
                salvar_json(ARQ_USERS, db, sha, "Pass"); st.success("Ok!")
            else: st.error("Senhas diferentes.")
    with tab3:
        with st.form("conf"):
            cn = st.text_input("Nome", NOME_ESCOLA); cc = st.color_picker("Cor", COR_TEMA); cl = st.text_input("Logo", LOGO_URL)
            if st.form_submit_button("Salvar"):
                salvar_json(ARQ_CONFIG, {"school_name": cn, "theme_color": cc, "logo_url": cl}, config_sha, "Config"); st.rerun()
