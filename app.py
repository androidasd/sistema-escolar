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

# --- FUNÇÕES DE SEGURANÇA E EMAIL ---

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

def enviar_email_boas_vindas(destinatario, nome_usuario):
    """Envia o e-mail automático usando o Gmail"""
    try:
        # Pega os dados dos Secrets
        remetente = st.secrets["EMAIL_USER"]
        senha_app = st.secrets["EMAIL_PASSWORD"]
        
        # GARANTIA: Remove qualquer espaço em branco que tenha ficado na senha
        senha_app = senha_app.replace(" ", "").strip()
        remetente = remetente.strip()
        
        # Cria a mensagem
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = "Cadastro Recebido - Sistema Escolar"
        
        texto = f"""
        Olá!
        
        Recebemos sua solicitação de cadastro no Sistema Escolar.
        
        Usuário: {nome_usuario}
        Situação: PENDENTE DE APROVAÇÃO
        
        Por favor, aguarde. Assim que o administrador confirmar seus dados, 
        você receberá acesso total ao sistema.
        
        Atenciosamente,
        Administração Escolar
        """
        msg.attach(MIMEText(texto, 'plain'))
        
        # Conecta no Gmail e envia
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
    # Tenta encontrar o repositório automaticamente
    for repo in user.get_repos():
        if "sistema" in repo.name.lower() or "escolar" in repo.name.lower() or "emeif" in repo.name.lower():
            repo_ref = repo
            break
    # Se não achar pelo nome, pega o primeiro da lista (fallback)
    if not repo_ref: 
        repos = list(user.get_repos())
        if repos: repo_ref = repos[0]
            
    if not repo_ref:
        st.error("Erro Crítico: Repositório não encontrado no GitHub.")
        st.stop()
except Exception as e:
    st.error(f"Erro de conexão com GitHub: {e}")
    st.stop()

# --- ARQUIVOS NO GITHUB ---
ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'
ARQ_USERS = 'users.json'
ARQ_CONFIG = 'config.json'

# --- FUNÇÕES DE MANIPULAÇÃO DE DADOS ---

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

# --- CONFIGURAÇÃO VISUAL DO TEMA ---
config_data, config_sha = carregar_json(ARQ_CONFIG)
COR_TEMA = config_data.get("theme_color", "#00A8C6")
NOME_ESCOLA = config_data.get("school_name", "SISTEMA ESCOLAR")
LOGO_URL = config_data.get("logo_url", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

st.set_page_config(page_title=NOME_ESCOLA, page_icon="🎓", layout="wide")

# CSS CSS PERSONALIZADO (LOGIN MODERNO)
st.markdown(f"""
<style>
    :root {{ --primary-color: {COR_TEMA}; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
    
    /* Login Centralizado e Moderno */
    .login-box {{
        background-color: white;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.1);
        text-align: center;
    }}
    
    .profile-container {{
        padding: 10px; border-bottom: 2px solid {COR_TEMA};
        margin-bottom: 20px; background: white; border-radius: 8px; cursor: pointer;
    }}
    .profile-popup {{
        display: none; position: absolute; top: 0; left: 105%; width: 280px;
        background: white; border: 1px solid #ccc; padding: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2); z-index: 999;
    }}
    .profile-container:hover .profile-popup {{ display: block; }}
    
    div.stButton > button:first-child {{ background-color: {COR_TEMA}; color: white; border-radius: 8px; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

# --- TELA DE LOGIN (MODERNA E CENTRALIZADA) ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None

if not st.session_state['user_info']:
    # Cria 3 colunas para centralizar o conteúdo no meio (coluna 2)
    col_esq, col_centro, col_dir = st.columns([1, 1.5, 1])
    
    with col_centro:
        # Espaçamento superior
        st.write("")
        st.write("")
        
        # Container com borda (Estilo Cartão)
        with st.container(border=True):
            # Logo e Título centralizados
            c_img, c_tit = st.columns([1, 3])
            with c_img:
                st.image(LOGO_URL, width=70)
            with c_tit:
                st.markdown(f"<h2 style='margin-top:0px; color: {COR_TEMA};'>{NOME_ESCOLA}</h2>", unsafe_allow_html=True)
            
            st.divider()
            
            # Abas de Login
            tab1, tab2 = st.tabs(["🔐 ENTRAR", "📝 CRIAR CONTA"])
            
            with tab1:
                with st.form("login"):
                    u = st.text_input("Usuário")
                    s = st.text_input("Senha", type="password")
                    # Botão Grande
                    if st.form_submit_button("ACESSAR SISTEMA", use_container_width=True):
                        # Verifica Admin Mestre
                        try:
                            senha_sistema = st.secrets["SENHA_SISTEMA"]
                        except:
                            senha_sistema = "admin"
                        
                        if u == "admin" and s == senha_sistema:
                             st.session_state['user_info'] = {
                                 "username": "admin", "name": "Super Admin", 
                                 "role": "admin", "email": "admin@sistema", "unit": "DIRETORIA"
                             }
                             st.rerun()
                        
                        # Verifica Banco de Dados
                        db, _ = carregar_json(ARQ_USERS)
                        users = db.get("users", [])
                        found = next((x for x in users if x['username'] == u and x['password'] == hash_senha(s)), None)
                        
                        if found:
                            if found.get('status') == 'active':
                                st.session_state['user_info'] = found
                                st.rerun()
                            else: st.warning("🔒 Conta aguardando aprovação.")
                        else: st.error("❌ Usuário ou senha incorretos.")
                        
            with tab2:
                with st.form("reg"):
                    st.caption("Preencha seus dados para solicitar acesso:")
                    nn = st.text_input("Nome Completo")
                    ne = st.text_input("E-mail Pessoal")
                    nu = st.text_input("Usuário (Login)")
                    ns = st.text_input("Senha", type="password")
                    
                    if st.form_submit_button("CRIAR CONTA", use_container_width=True):
                        db, sha = carregar_json(ARQ_USERS)
                        lst = db.get("users", [])
                        if any(x['username'] == nu for x in lst): st.error("⚠️ Este usuário já existe.")
                        else:
                            with st.spinner("Enviando solicitação..."):
                                lst.append({"username": nu, "password": hash_senha(ns), "name": nn, "email": ne, "role": "user", "status": "pending", "unit": "PADRÃO"})
                                if not db: db = {"users": []}
                                db['users'] = lst
                                salvar_json(ARQ_USERS, db, sha, f"Novo user {nu}")
                                
                                sucesso, mensagem_erro = enviar_email_boas_vindas(ne, nu)
                                
                                if sucesso:
                                    st.success(f"✅ Conta criada! Verifique seu e-mail: {ne}")
                                else:
                                    st.warning(f"⚠️ Conta salva, mas erro no e-mail: {mensagem_erro}")
    st.stop()

# --- SISTEMA LOGADO (DASHBOARD) ---
user = st.session_state['user_info']

with st.sidebar:
    st.image(LOGO_URL, width=80)
    # Card de Perfil
    st.markdown(f"""
    <div class="profile-container">
        👤 <strong>{user['username']}</strong>
        <div class="profile-popup">
            <strong>{user['name']}</strong><br>{user.get('email')}<br>
            <span style="color:blue">{user['role'].upper()}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    from streamlit_option_menu import option_menu
    opts = ["Dashboard", "Pesquisar", "Cadastrar Aluno"]
    icons = ["house", "search", "person-plus"]
    if user['role'] == 'admin':
        opts.append("Administração"); icons.append("gear")
    
    menu = option_menu("Menu", opts, icons=icons, default_index=0)
    if st.button("Sair"): st.session_state['user_info'] = None; st.rerun()

# --- CARREGAR DADOS DOS ALUNOS ---
if menu in ["Dashboard", "Pesquisar"]:
    df = pd.DataFrame(carregar_dados_word())

# --- TELAS DO SISTEMA ---
if menu == "Administração":
    st.title("⚙️ Painel Admin")
    tab_u, tab_c = st.tabs(["👥 Usuários", "🎨 Aparência"])
    with tab_u:
        db, sha = carregar_json(ARQ_USERS)
        if db.get("users"):
            edited = st.data_editor(
                pd.DataFrame(db['users']), 
                key="user_edit", 
                num_rows="dynamic",
                column_config={
                    "status": st.column_config.SelectboxColumn("Status", options=["active", "pending", "disabled"]),
                    "role": st.column_config.SelectboxColumn("Permissão", options=["user", "admin"])
                }
            )
            if st.button("Salvar Alterações de Usuários"):
                db['users'] = edited.to_dict('records')
                salvar_json(ARQ_USERS, db, sha, "Update users")
                st.success("Usuários atualizados!"); time.sleep(1); st.rerun()
        else:
            st.info("Nenhum usuário cadastrado.")
            
    with tab_c:
        with st.form("conf"):
            cn = st.text_input("Nome Escola", NOME_ESCOLA)
            cc = st.color_picker("Cor do Tema", COR_TEMA)
            cl = st.text_input("URL da Logo", LOGO_URL)
            if st.form_submit_button("Salvar Configuração"):
                _, s_c = carregar_json(ARQ_CONFIG)
                salvar_json(ARQ_CONFIG, {"school_name": cn, "theme_color": cc, "logo_url": cl}, s_c, "Update config")
                st.success("Tema atualizado!"); time.sleep(2); st.rerun()

elif menu == "Dashboard":
    st.title("📊 Visão Geral")
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("Total Alunos", len(df))
        c2.metric("Concluintes", len(df[df['Categoria']=="Concluinte"]))
        st.subheader("Últimos Registros")
        st.dataframe(df.tail(5), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado encontrado nos arquivos Word.")

elif menu == "Pesquisar":
    st.title("🔍 Buscar Aluno")
    busca = st.text_input("Digite o nome:", placeholder="Ex: Maria...")
    if busca and not df.empty:
        res = df[df['Nome'].str.contains(busca.upper(), na=False)]
        if not res.empty:
            st.success(f"{len(res)} alunos encontrados.")
            st.dataframe(res, use_container_width=True, hide_index=True)
        else: st.warning("Nenhum aluno encontrado com esse nome.")
    else: st.info("Digite um nome acima para iniciar a pesquisa.")

elif menu == "Cadastrar Aluno":
    st.title("📝 Nova Matrícula")
    with st.form("novo_aluno"):
        c1, c2 = st.columns([1,4])
        num = c1.text_input("Nº (Ex: 050)")
        nome = c2.text_input("Nome Completo")
        tipo = st.radio("Arquivo de Destino", ["Passivos", "Concluintes"])
        obs = st.text_input("Observação")
        
        if st.form_submit_button("💾 SALVAR ALUNO"):
            arq = ARQ_PASSIVOS if tipo == "Passivos" else ARQ_CONCLUINTES
            if not num: num = "S/N"
            if salvar_aluno_word(arq, num, nome, obs):
                st.success(f"Aluno {nome} salvo com sucesso no arquivo Word!")
                time.sleep(1)
                st.cache_data.clear()
                st.rerun()
            else: st.error("Erro ao salvar no GitHub.")
