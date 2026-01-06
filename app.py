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
from streamlit_option_menu import option_menu

# --- CONFIGURAÇÃO DA PÁGINA (DEVE SER A PRIMEIRA COISA) ---
# Tenta carregar configs locais antes de conectar, apenas para pegar o nome
# Mas como precisamos conectar no Github para pegar o config.json, definimos um padrão primeiro.
ST_COR_PADRAO = "#00A8C6"
ST_TITULO_PADRAO = "SISTEMA ESCOLAR"

st.set_page_config(page_title=ST_TITULO_PADRAO, page_icon="🎓", layout="wide")

# --- FUNÇÕES DE SEGURANÇA E EMAIL ---
def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

def enviar_email_boas_vindas(destinatario, nome_usuario):
    try:
        remetente = st.secrets["EMAIL_USER"]
        senha_app = st.secrets["EMAIL_PASSWORD"]
        senha_app = senha_app.replace(" ", "").strip()
        remetente = remetente.strip()
        
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = "Acesso Solicitado - Sistema Escolar"
        
        texto = f"""
        Olá, {nome_usuario}!
        Recebemos sua solicitação de cadastro.
        Login: {destinatario}
        Situação: PENDENTE DE APROVAÇÃO.
        Aguarde a liberação do administrador.
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
    for repo in user.get_repos():
        if "sistema" in repo.name.lower() or "escolar" in repo.name.lower() or "emeif" in repo.name.lower():
            repo_ref = repo
            break
    if not repo_ref: 
        repos = list(user.get_repos())
        if repos: repo_ref = repos[0]
    if not repo_ref:
        st.error("Erro Crítico: Repositório não encontrado.")
        st.stop()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
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
        if sha: repo_ref.update_file(arquivo, mensagem, dados_str, sha)
        else: repo_ref.create_file(arquivo, mensagem, dados_str)
        return True
    except: return False

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
        except: return []
    return processar(ARQ_PASSIVOS, "Passivo") + processar(ARQ_CONCLUINTES, "Concluinte")

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

# --- CARREGA PREFERÊNCIAS VISUAIS ---
config_data, config_sha = carregar_json(ARQ_CONFIG)
COR_TEMA = config_data.get("theme_color", ST_COR_PADRAO)
NOME_ESCOLA = config_data.get("school_name", ST_TITULO_PADRAO)
LOGO_URL = config_data.get("logo_url", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

# --- CSS PREMIUM E MODERNO ---
st.markdown(f"""
<style>
    /* Importando fonte bonita */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Roboto', sans-serif;
    }}
    
    /* Remove padding excessivo do Streamlit */
    .block-container {{ padding-top: 1rem; padding-bottom: 5rem; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}

    /* VARIÁVEIS DE COR */
    :root {{
        --primary: {COR_TEMA};
        --light-bg: #f8f9fa;
        --card-bg: #ffffff;
        --text-dark: #2c3e50;
    }}

    /* ESTILO DOS CARDS (MÉTRICAS) */
    div[data-testid="metric-container"] {{
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid var(--primary);
        text-align: center;
    }}

    /* BOTÕES */
    div.stButton > button:first-child {{
        background-color: var(--primary);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: 0.3s;
    }}
    div.stButton > button:first-child:hover {{
        opacity: 0.9;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}

    /* LOGIN CENTRALIZADO */
    .login-container {{
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }}
    
    /* CONTAINER DO HEADER (TOPO) */
    .header-style {{
        background-color: white;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 3px solid var(--primary);
    }}
</style>
""", unsafe_allow_html=True)

# --- LÓGICA DE SESSÃO ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None

# ==============================================================================
# TELA DE LOGIN (DESIGN LIMPO)
# ==============================================================================
if not st.session_state['user_info']:
    col_e, col_c, col_d = st.columns([1, 1.5, 1])
    with col_c:
        st.write("")
        st.write("")
        # Simula um "Card" usando container
        with st.container():
            st.markdown(f"""
            <div class="login-container" style="text-align:center;">
                <img src="{LOGO_URL}" width="100" style="margin-bottom:15px;">
                <h2 style="color:{COR_TEMA}; margin:0;">{NOME_ESCOLA}</h2>
                <p style="color:gray;">Portal de Gestão Acadêmica</p>
                <hr style="opacity:0.2">
            </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["🔐 ACESSAR", "📝 CADASTRAR"])
            
            with tab1:
                with st.form("login_frm"):
                    email = st.text_input("E-mail")
                    senha = st.text_input("Senha", type="password")
                    if st.form_submit_button("ENTRAR", use_container_width=True):
                        try: s_adm = st.secrets["SENHA_SISTEMA"]
                        except: s_adm = "admin"
                        
                        if email.lower() == "admin@escola.com" and senha == s_adm:
                            st.session_state['user_info'] = {"username": "Admin", "name": "Super Administrador", "role": "admin", "email": "admin@escola.com", "unit": "Diretoria"}
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
                                with st.spinner("Registrando..."):
                                    lst.append({"username": e.split("@")[0], "password": hash_senha(s), "name": n, "email": e, "role": "user", "status": "pending", "unit": "Geral"})
                                    if not db: db = {"users": []}
                                    db['users'] = lst
                                    salvar_json(ARQ_USERS, db, sha, f"Reg {e}")
                                    env, erro = enviar_email_boas_vindas(e, n)
                                    if env: st.success("Verifique seu e-mail!")
                                    else: st.warning(f"Salvo, mas erro no email: {erro}")
    st.stop()

# ==============================================================================
# ÁREA LOGADA - LAYOUT PREMIUM
# ==============================================================================
user = st.session_state['user_info']

# --- HEADER (CABEÇALHO) PERSONALIZADO ---
# Usamos colunas nativas do Streamlit para evitar erros de HTML/CSS
with st.container():
    # Estilo de fundo branco e logo
    c_logo, c_menu_fake, c_user = st.columns([2, 0.5, 3])
    
    with c_logo:
        # Logo e Nome Lado a Lado
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:15px;">
            <img src="{LOGO_URL}" width="50">
            <div>
                <h3 style="margin:0; color:{COR_TEMA}; font-weight:800;">{NOME_ESCOLA}</h3>
                <small style="color:gray;">Sistema de Gestão</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_user:
        # Área do Usuário + Botão Sair alinhados a direita
        c_u_info, c_u_btn = st.columns([3, 1])
        with c_u_info:
            st.markdown(f"""
            <div style="text-align:right; line-height:1.2;">
                <span style="font-weight:bold; color:#333;">{user['name']}</span><br>
                <span style="font-size:12px; color:{COR_TEMA}; background:#ebfbfc; padding:2px 8px; border-radius:10px;">{user['role'].upper()}</span>
            </div>
            """, unsafe_allow_html=True)
        with c_u_btn:
            if st.button("SAIR", key="logout_top"):
                st.session_state['user_info'] = None
                st.rerun()

st.divider()

# --- MENU DE NAVEGAÇÃO HORIZONTAL (MUITO MAIS BONITO) ---
# Se for admin mostra menu extra
opts = ["Dashboard", "Pesquisar", "Cadastrar Aluno"]
icons = ["house", "search", "person-plus"]
if user['role'] == 'admin':
    opts.append("Administração"); icons.append("gear")

selected = option_menu(
    menu_title=None,
    options=opts,
    icons=icons,
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#ffffff", "border-radius": "5px"},
        "icon": {"color": COR_TEMA, "font-size": "16px"},
        "nav-link": {"font-size": "15px", "text-align": "center", "margin": "0px", "--hover-color": "#f0f2f6"},
        "nav-link-selected": {"background-color": COR_TEMA, "color": "white"},
    }
)

st.write("") # Espaço

# --- CONTEÚDO DAS PÁGINAS ---
if selected in ["Dashboard", "Pesquisar"]:
    df = pd.DataFrame(carregar_dados_word())

if selected == "Dashboard":
    st.subheader("📊 Visão Geral")
    if not df.empty:
        # Cards de Métricas Estilizados (O CSS já cuida da beleza)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Alunos", len(df))
        col2.metric("Concluintes", len(df[df['Categoria']=="Concluinte"]))
        col3.metric("Passivos", len(df[df['Categoria']=="Passivo"]))
        
        st.write("")
        st.markdown("##### 📌 Últimas Atualizações")
        # Tabela limpa
        st.dataframe(
            df.tail(10), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Categoria": st.column_config.TextColumn("Status", width="medium"),
                "Nome": st.column_config.TextColumn("Nome do Aluno", width="large")
            }
        )
    else:
        st.info("Nenhum dado carregado. Verifique os arquivos no GitHub.")

elif selected == "Pesquisar":
    st.subheader("🔍 Buscar Aluno")
    # Barra de pesquisa moderna
    busca = st.text_input("Digite o nome do aluno...", placeholder="Ex: Maria da Silva")
    
    if busca and not df.empty:
        res = df[df['Nome'].str.contains(busca.upper(), na=False)]
        if not res.empty:
            st.success(f"{len(res)} registros encontrados.")
            st.dataframe(res, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum aluno encontrado.")
    elif not busca:
        st.info("Utilize a barra acima para pesquisar.")

elif selected == "Cadastrar Aluno":
    st.subheader("📝 Nova Matrícula")
    # Container branco para o formulário
    with st.container():
        with st.form("novo_aluno_form"):
            c1, c2 = st.columns([1, 4])
            num = c1.text_input("Nº Chamada", placeholder="000")
            nome = c2.text_input("Nome Completo")
            
            c3, c4 = st.columns(2)
            tipo = c3.radio("Situação", ["Passivos", "Concluintes"], horizontal=True)
            obs = c4.text_input("Observação (Opcional)")
            
            st.write("")
            if st.form_submit_button("💾 SALVAR ALUNO", use_container_width=True):
                arq = ARQ_PASSIVOS if tipo == "Passivos" else ARQ_CONCLUINTES
                if not num: num = "S/N"
                if salvar_aluno_word(arq, num, nome, obs):
                    st.toast(f"Aluno {nome} salvo com sucesso!", icon="✅")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Erro ao salvar no GitHub.")

elif selected == "Administração":
    st.subheader("⚙️ Painel de Controle")
    
    tab_users, tab_pass, tab_config = st.tabs(["Gestão de Usuários", "Senhas", "Configurações"])
    
    with tab_users:
        db, sha = carregar_json(ARQ_USERS)
        if db.get("users"):
            users_df = pd.DataFrame(db['users'])
            cols = ["name", "email", "status", "role", "unit"]
            # Garante que as colunas existem
            show_df = users_df[[c for c in cols if c in users_df.columns]]
            
            edited = st.data_editor(
                show_df, 
                key="editor_users", 
                use_container_width=True,
                column_config={
                    "status": st.column_config.SelectboxColumn("Acesso", options=["active", "pending", "disabled"]),
                    "role": st.column_config.SelectboxColumn("Permissão", options=["user", "admin"])
                }
            )
            
            if st.button("Salvar Alterações de Acesso"):
                novos = edited.to_dict('records')
                # Mescla inteligente
                lista_final = []
                for n in novos:
                    orig = next((u for u in db['users'] if u['email'] == n['email']), None)
                    if orig: orig.update(n); lista_final.append(orig)
                    else: lista_final.append(n)
                
                db['users'] = lista_final
                salvar_json(ARQ_USERS, db, sha, "Update Users")
                st.success("Dados atualizados!")
                time.sleep(1); st.rerun()
                
    with tab_pass:
        st.write("Redefinir senha de usuário:")
        db, sha = carregar_json(ARQ_USERS)
        lst = db.get("users", [])
        sel_user = st.selectbox("Selecione:", [u['email'] for u in lst])
        if sel_user:
            p1 = st.text_input("Nova Senha", type="password")
            p2 = st.text_input("Repita a Senha", type="password")
            if st.button("Alterar Senha"):
                if p1 == p2:
                    for u in lst:
                        if u['email'] == sel_user: u['password'] = hash_senha(p1)
                    db['users'] = lst
                    salvar_json(ARQ_USERS, db, sha, "Update pass")
                    st.success("Senha alterada.")
                else: st.error("Senhas não conferem.")

    with tab_config:
        st.write("Personalizar Sistema:")
        with st.form("conf_geral"):
            cn = st.text_input("Nome da Escola", NOME_ESCOLA)
            cc = st.color_picker("Cor Principal", COR_TEMA)
            cl = st.text_input("URL da Logo", LOGO_URL)
            if st.form_submit_button("Salvar Aparência"):
                _, s_c = carregar_json(ARQ_CONFIG)
                salvar_json(ARQ_CONFIG, {"school_name": cn, "theme_color": cc, "logo_url": cl}, s_c, "Upd Config")
                st.toast("Configurações salvas. Atualizando...")
                time.sleep(2); st.rerun()
