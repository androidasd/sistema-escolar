import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io
import time
import json
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit_option_menu import option_menu # Importação movida para o topo

# --- FUNÇÕES DE SEGURANÇA E EMAIL ---

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

def enviar_email_boas_vindas(destinatario, nome_usuario):
    """Envia o e-mail automático usando o Gmail"""
    try:
        remetente = st.secrets["EMAIL_USER"]
        senha_app = st.secrets["EMAIL_PASSWORD"]
        
        # Limpeza de segurança nos dados
        senha_app = senha_app.replace(" ", "").strip()
        remetente = remetente.strip()
        
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = "Acesso Solicitado - Sistema Escolar"
        
        texto = f"""
        Olá, {nome_usuario}!
        
        Recebemos sua solicitação de cadastro.
        
        Seu Login: {destinatario}
        Situação Atual: PENDENTE DE APROVAÇÃO
        
        Por favor, aguarde. Assim que a direção confirmar seus dados, 
        você receberá acesso total ao sistema.
        
        Atenciosamente,
        Gestão Escolar
        """
        msg.attach(MIMEText(texto, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha_app)
        server.sendmail(remetente, destinatario, msg.as_string())
        server.quit()
        return True, "Enviado"
    except Exception as e:
        return False, str(e)

# --- CONEXÃO GITHUB ---
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    g = Github(TOKEN)
    user = g.get_user()
    repo_ref = None
    # Busca inteligente do repositório
    for repo in user.get_repos():
        if "sistema" in repo.name.lower() or "escolar" in repo.name.lower() or "emeif" in repo.name.lower():
            repo_ref = repo
            break
    if not repo_ref: 
        repos = list(user.get_repos())
        if repos: repo_ref = repos[0]
            
    if not repo_ref:
        st.error("Erro Crítico: Repositório não encontrado no GitHub.")
        st.stop()
except Exception as e:
    st.error(f"Erro de conexão com GitHub: {e}")
    st.stop()

# --- ARQUIVOS ---
ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'
ARQ_USERS = 'users.json'
ARQ_CONFIG = 'config.json'

# --- MANIPULAÇÃO DE DADOS ---

def carregar_json(arquivo):
    try:
        content = repo_ref.get_contents(arquivo)
        return json.loads(content.decoded_content.decode()), content.sha
    except:
        return {}, None

def salvar_json(arquivo, dados, sha, mensagem):
    try:
        dados_str = json.dumps(dados, indent=4)
        if sha:
            repo_ref.update_file(arquivo, mensagem, dados_str, sha)
        else:
            repo_ref.create_file(arquivo, mensagem, dados_str)
        return True
    except:
        return False

@st.cache_data(ttl=60)
def carregar_dados_word():
    lista = []
    def processar(nome_arq, categoria):
        local = []
        try:
            c = repo_ref.get_contents(nome_arq)
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
        except:
            return []
    l1 = processar(ARQ_PASSIVOS, "Passivo")
    l2 = processar(ARQ_CONCLUINTES, "Concluinte")
    return l1 + l2

def salvar_aluno_word(arquivo_nome, numero, nome, obs):
    try:
        c = repo_ref.get_contents(arquivo_nome)
        doc = Document(io.BytesIO(c.decoded_content))
        if len(doc.tables) > 0:
            tab = doc.tables[0]
            row = tab.add_row()
            row.cells[0].text = numero
            row.cells[1].text = nome.upper()
            if len(row.cells) > 2: row.cells[2].text = obs
            buffer = io.BytesIO()
            doc.save(buffer)
            repo_ref.update_file(arquivo_nome, f"Add Aluno: {nome}", buffer.getvalue(), c.sha)
            return True
    except: return False

# --- CONFIGURAÇÃO INICIAL E TEMA ---
config_data, config_sha = carregar_json(ARQ_CONFIG)
COR_TEMA = config_data.get("theme_color", "#00A8C6")
NOME_ESCOLA = config_data.get("school_name", "SISTEMA ESCOLAR")
LOGO_URL = config_data.get("logo_url", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

st.set_page_config(page_title=NOME_ESCOLA, page_icon="🎓", layout="wide")

# --- CSS GLOBAL E DA NAVBAR SUPERIOR ---
st.markdown(f"""
<style>
    :root {{ --primary-color: {COR_TEMA}; }}
    #MainMenu {{visibility: hidden;}} 
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}} /* Esconde cabeçalho padrão do Streamlit */
    
    /* Ajuste de padding para o conteúdo não ficar debaixo da navbar */
    .block-container {{ padding-top: 1rem; }}

    /* CSS da Tela de Login */
    .stTabs [data-baseweb="tab-list"] {{ justify-content: center; }}
    
    /* Botões */
    div.stButton > button:first-child {{
        background-color: {COR_TEMA}; color: white; border-radius: 8px; font-weight: bold; border: none;
    }}
    div.stButton > button:first-child:hover {{ opacity: 0.9; }}

    /* --- CSS DA NOVA BARRA SUPERIOR (NAVBAR) --- */
    
    /* Container principal da barra superior */
    .top-navbar-container {{
        background-color: {COR_TEMA};
        padding: 0.5rem 1rem;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        color: white;
        display: flex; align-items: center;
    }}

    /* Estilo do Cartão de Perfil na Barra Superior */
    .top-profile-container {{
        display: flex;
        align-items: center;
        justify-content: flex-end;
        cursor: pointer;
        color: white;
        position: relative;
        padding: 5px;
    }}
    .top-profile-popup {{
        display: none;
        position: absolute;
        top: 100%; /* Abre para baixo */
        right: 0;   /* Alinhado à direita */
        width: 250px;
        background: white;
        color: black; /* Texto preto dentro do popup */
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        padding: 15px;
        z-index: 1000;
        text-align: left;
    }}
    .top-profile-container:hover .top-profile-popup {{ display: block; }}
    
    /* Ajuste fino para o menu horizontal ficar transparente na barra */
    [data-testid="stHorizontalBlock"] .st-emotion-cache-1ybti6c {{
        background-color: transparent !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- LÓGICA DE SESSÃO ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None

# --- TELA DE LOGIN (Centralizada) ---
if not st.session_state['user_info']:
    col_esq, col_centro, col_dir = st.columns([1, 1.2, 1])
    with col_centro:
        st.write("")
        with st.container(border=True):
            st.markdown(f"""
                <div style="text-align: center; padding-bottom: 20px;">
                    <img src="{LOGO_URL}" width="80" style="margin-bottom: 10px;">
                    <h2 style="margin: 0; color: {COR_TEMA}; font-weight: 700;">{NOME_ESCOLA}</h2>
                </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["🔐 ENTRAR", "📝 CRIAR CONTA"])
            
            with tab1:
                with st.form("login_email"):
                    email_login = st.text_input("E-mail")
                    senha_login = st.text_input("Senha", type="password")
                    if st.form_submit_button("ACESSAR SISTEMA", use_container_width=True):
                        try: s_mestra = st.secrets["SENHA_SISTEMA"]
                        except: s_mestra = "admin"
                        if email_login.lower() == "admin@escola.com" and senha_login == s_mestra:
                             st.session_state['user_info'] = {"username": "Super Admin", "name": "Administrador Geral", "role": "admin", "email": "admin@escola.com", "unit": "DIRETORIA"}
                             st.rerun()
                        db, _ = carregar_json(ARQ_USERS)
                        users = db.get("users", [])
                        found = next((x for x in users if x.get('email', '').lower() == email_login.lower() and x['password'] == hash_senha(senha_login)), None)
                        if found:
                            if found.get('status') == 'active':
                                st.session_state['user_info'] = found
                                st.rerun()
                            else: st.warning("🔒 Conta em análise.")
                        else: st.error("❌ E-mail ou senha incorretos.")

            with tab2:
                with st.form("registro"):
                    nome_reg = st.text_input("Nome Completo")
                    email_reg = st.text_input("E-mail Pessoal")
                    senha_reg = st.text_input("Crie uma Senha", type="password")
                    if st.form_submit_button("SOLICITAR CADASTRO", use_container_width=True):
                        if not email_reg or "@" not in email_reg: st.error("E-mail inválido.")
                        else:
                            db, sha = carregar_json(ARQ_USERS)
                            lst = db.get("users", [])
                            if any(x.get('email', '').lower() == email_reg.lower() for x in lst): st.error("E-mail já cadastrado.")
                            else:
                                with st.spinner("Enviando..."):
                                    lst.append({"username": email_reg.split("@")[0], "password": hash_senha(senha_reg), "name": nome_reg, "email": email_reg, "role": "user", "status": "pending", "unit": "PADRÃO"})
                                    if not db: db = {"users": []}
                                    db['users'] = lst
                                    salvar_json(ARQ_USERS, db, sha, f"Novo registro: {email_reg}")
                                    sucesso, msg_erro = enviar_email_boas_vindas(email_reg, nome_reg)
                                    if sucesso: st.success(f"✅ Solicitação enviada para: {email_reg}")
                                    else: st.warning(f"⚠️ Salvo, erro no e-mail: {msg_erro}")
    st.stop()

# ==============================================================================
# ÁREA LOGADA COM BARRA SUPERIOR (NAVBAR)
# ==============================================================================
user = st.session_state['user_info']

# --- CONSTRUÇÃO DA BARRA SUPERIOR ---
# Usamos um container com cor de fundo para simular a barra, e colunas dentro.
with st.container():
    # Injeta o estilo do container da navbar
    st.markdown(f'<div class="top-navbar-container">', unsafe_allow_html=True)
    
    # Divide a barra em 3 partes: [Logo/Titulo] [Menu Horizontal] [Perfil]
    nav_col1, nav_col2, nav_col3 = st.columns([1.5, 3, 1.2])
    
    with nav_col1:
        # Logo e Título na esquerda (texto branco)
        st.markdown(f"""
            <div style="display: flex; align-items: center;">
                <img src="{LOGO_URL}" width="40" style="margin-right: 10px;">
                <h4 style="margin: 0; color: white; font-weight: 700; white-space: nowrap;">{NOME_ESCOLA}</h4>
            </div>
        """, unsafe_allow_html=True)
        
    with nav_col2:
        # Menu Horizontal no centro
        opts = ["Dashboard", "Pesquisar", "Cadastrar Aluno"]
        icons = ["house", "search", "person-plus"]
        if user['role'] == 'admin':
            opts.append("Administração"); icons.append("gear")
            
        # Estilo personalizado para o menu ficar transparente e com texto branco
        menu = option_menu(None, opts, icons=icons, default_index=0, orientation="horizontal",
                           styles={
                               "container": {"padding": "0!important", "background-color": "transparent"},
                               "icon": {"color": "white", "font-size": "14px"}, 
                               "nav-link": {"color": "white", "font-size": "14px", "text-align": "center", "margin":"0px", "--hover-color": "rgba(255,255,255,0.2)"},
                               "nav-link-selected": {"background-color": "rgba(255,255,255,0.3)"},
                           })

    with nav_col3:
        # Perfil e Logout na direita
        # O botão de sair agora fica dentro do popup do perfil para economizar espaço
        html_perfil_top = f"""
        <div class="top-profile-container">
            <div style="text-align: right; margin-right: 10px;">
                <small>Olá,</small><br><strong>{user['name'].split()[0]}</strong>
            </div>
            <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" width="35" style="border-radius: 50%; border: 2px solid white;">
            
            <div class="top-profile-popup">
                <div style="border-bottom: 1px solid #eee; padding-bottom: 10px; margin-bottom: 10px;">
                    <strong>{user['name']}</strong><br>
                    <small>{user.get('email')}</small><br>
                    <span style="color:{COR_TEMA}; font-weight:bold;">{user['role'].upper()}</span>
                </div>
                </div>
        </div>
        """
        st.markdown(html_perfil_top, unsafe_allow_html=True)
        
        # Botão de sair invisível que é ativado pelo CSS do popup (truque para usar st.button)
        with st.container():
             if st.button("🔒 Sair do Sistema", key="top_logout_btn", use_container_width=True):
                 st.session_state['user_info'] = None
                 st.rerun()

    st.markdown('</div>', unsafe_allow_html=True) # Fecha container da navbar

# --- LÓGICA DE DADOS E TELAS (Conteúdo principal abaixo da barra) ---
if menu in ["Dashboard", "Pesquisar"]:
    df = pd.DataFrame(carregar_dados_word())

if menu == "Administração":
    st.markdown(f"## ⚙️ Administração do Sistema")
    tab_u, tab_p, tab_c = st.tabs(["👥 Usuários", "🔑 Alterar Senhas", "🎨 Aparência"])
    with tab_u:
        db, sha = carregar_json(ARQ_USERS)
        users_list = db.get("users", [])
        if users_list:
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Total", len(users_list))
            col_m2.metric("Pendentes", len([u for u in users_list if u.get('status') == 'pending']))
            
            df_users = pd.DataFrame(users_list)
            cols = ["name", "email", "status", "role", "unit"]
            df_display = df_users[[c for c in cols if c in df_users.columns]]
            edited = st.data_editor(df_display, key="user_ed", use_container_width=True,
                column_config={"status": st.column_config.SelectboxColumn("Status", options=["active", "pending", "disabled"]),
                               "role": st.column_config.SelectboxColumn("Nível", options=["user", "admin"])})
            if st.button("💾 Salvar Status"):
                novos = edited.to_dict('records')
                lista_atual = []
                for novo in novos:
                    orig = next((u for u in users_list if u.get('email') == novo['email']), None)
                    if orig: orig.update(novo); lista_atual.append(orig)
                    else: lista_atual.append(novo)
                db['users'] = lista_atual
                salvar_json(ARQ_USERS, db, sha, "Update users"); st.success("Salvo!"); time.sleep(1); st.rerun()
    with tab_p:
        st.markdown("### 🔐 Redefinir Senha")
        db, sha = carregar_json(ARQ_USERS)
        ul = db.get("users", [])
        emails = [u.get('email') for u in ul]
        us = st.selectbox("Usuário:", [""] + emails)
        if us:
            ns = st.text_input("Nova Senha", type="password")
            cs = st.text_input("Confirme", type="password")
            if st.button("Alterar Senha"):
                if ns and ns == cs:
                    for u in ul:
                        if u.get('email') == us: u['password'] = hash_senha(ns); break
                    db['users'] = ul
                    salvar_json(ARQ_USERS, db, sha, f"Senha alterada {us}"); st.success("Senha alterada!")
                else: st.error("Senhas não conferem.")
    with tab_c:
        st.markdown("### 🎨 Personalização")
        with st.form("conf"):
            cn = st.text_input("Nome Escola", NOME_ESCOLA)
            cc = st.color_picker("Cor Tema", COR_TEMA)
            cl = st.text_input("URL Logo", LOGO_URL)
            if st.form_submit_button("Aplicar"):
                _, s_c = carregar_json(ARQ_CONFIG)
                salvar_json(ARQ_CONFIG, {"school_name": cn, "theme_color": cc, "logo_url": cl}, s_c, "Update config")
                st.toast("Atualizando..."); time.sleep(2); st.rerun()

elif menu == "Dashboard":
    st.markdown(f"## 📊 Visão Geral")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", len(df)); c2.metric("Concluintes", len(df[df['Categoria']=="Concluinte"])); c3.metric("Passivos", len(df[df['Categoria']=="Passivo"]))
        st.dataframe(df.tail(5), use_container_width=True, hide_index=True)
    else: st.info("Sem dados.")

elif menu == "Pesquisar":
    st.markdown("## 🔍 Consultar Aluno")
    busca = st.text_input("Busca por nome...")
    if busca and not df.empty:
        res = df[df['Nome'].str.contains(busca.upper(), na=False)]
        if not res.empty: st.success(f"{len(res)} encontrados."); st.dataframe(res, use_container_width=True, hide_index=True)
        else: st.warning("Não encontrado.")

elif menu == "Cadastrar Aluno":
    st.markdown("## 📝 Novo Aluno")
    with st.container(border=True):
        with st.form("novo"):
            c1, c2 = st.columns([1,4])
            num = c1.text_input("Nº")
            nome = c2.text_input("Nome")
            tipo = st.radio("Destino", ["Passivos", "Concluintes"], horizontal=True)
            obs = st.text_input("Obs")
            if st.form_submit_button("💾 SALVAR"):
                arq = ARQ_PASSIVOS if tipo == "Passivos" else ARQ_CONCLUINTES
                if not num: num = "S/N"
                if salvar_aluno_word(arq, num, nome, obs): st.balloons(); st.success("Salvo!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                else: st.error("Erro ao salvar.")
