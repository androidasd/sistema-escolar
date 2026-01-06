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

# --- FUNÇÕES UTILITÁRIAS ---

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

def enviar_email(destinatario, assunto, mensagem):
    try:
        sender_email = st.secrets["EMAIL_USER"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(mensagem, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, destinatario, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

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
    if not repo_ref: repo_ref = user.get_repos()[0]
except:
    st.error("Erro crítico: Configure os Secrets corretamente.")
    st.stop()

ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'
ARQ_USERS = 'users.json'
ARQ_CONFIG = 'config.json'

# --- GERENCIAMENTO DE DADOS JSON (GITHUB) ---

def carregar_json(arquivo):
    try:
        content = repo_ref.get_contents(arquivo)
        return json.loads(content.decoded_content.decode()), content.sha
    except:
        return {}, None

def salvar_json(arquivo, dados, sha, mensagem):
    try:
        dados_str = json.dumps(dados, indent=4)
        repo_ref.update_file(arquivo, mensagem, dados_str, sha)
        return True
    except:
        return False

# --- CARREGA CONFIGURAÇÕES INICIAIS ---
config_data, config_sha = carregar_json(ARQ_CONFIG)
COR_TEMA = config_data.get("theme_color", "#00A8C6")
NOME_ESCOLA = config_data.get("school_name", "SISTEMA ESCOLAR")
LOGO_URL = config_data.get("logo_url", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

st.set_page_config(page_title=NOME_ESCOLA, page_icon="🎓", layout="wide")

# --- CSS PERSONALIZADO (PERFIL E CORES) ---
st.markdown(f"""
<style>
    /* Variaveis de Cor */
    :root {{ --primary-color: {COR_TEMA}; }}
    
    /* Esconde menus padrao */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Estilo do Card de Perfil (Hover) */
    .profile-container {{
        position: relative;
        display: inline-block;
        padding: 10px;
        cursor: pointer;
        border-bottom: 2px solid {COR_TEMA};
        width: 100%;
        margin-bottom: 20px;
        background: white;
        border-radius: 8px;
    }}
    
    .profile-popup {{
        display: none;
        position: absolute;
        top: 0px;
        left: 105%; /* Aparece ao lado */
        width: 300px;
        background-color: #fff;
        border: 1px solid #ccc;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        z-index: 999;
        padding: 15px;
        color: black;
    }}
    
    .profile-container:hover .profile-popup {{
        display: block;
    }}

    .profile-header {{
        border-bottom: 2px solid {COR_TEMA};
        padding-bottom: 5px;
        margin-bottom: 10px;
        font-weight: bold;
        font-size: 18px;
        text-align: center;
    }}
    
    .profile-row {{ margin-bottom: 8px; font-size: 14px; }}
    .profile-label {{ font-weight: bold; color: #333; }}
    
    /* Botoes */
    div.stButton > button:first-child {{
        background-color: {COR_TEMA};
        color: white;
    }}
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN E CADASTRO ---

if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

def tela_login():
    st.markdown(f"<h1 style='text-align: center; color: {COR_TEMA};'>{NOME_ESCOLA}</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 LOGIN", "📝 CRIAR CONTA"])
    
    with tab1:
        with st.form("login_form"):
            user = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            btn_login = st.form_submit_button("ENTRAR")
            
            if btn_login:
                db_users, _ = carregar_json(ARQ_USERS)
                lista = db_users.get("users", [])
                
                usuario_encontrado = None
                for u in lista:
                    if u['username'] == user and u['password'] == hash_senha(senha):
                        usuario_encontrado = u
                        break
                
                if usuario_encontrado:
                    if usuario_encontrado['status'] == 'active':
                        st.session_state['user_info'] = usuario_encontrado
                        st.rerun()
                    elif usuario_encontrado['status'] == 'pending':
                        st.warning("⏳ Sua conta ainda está pendente de aprovação pelo Administrador.")
                    else:
                        st.error("🚫 Conta desativada.")
                else:
                    st.error("Usuário ou senha incorretos.")

    with tab2:
        st.info("Preencha para solicitar acesso. Você receberá um e-mail de confirmação.")
        with st.form("registro_form"):
            new_name = st.text_input("Nome Completo")
            new_email = st.text_input("Seu E-mail")
            new_unit = st.text_input("Unidade Escolar Padrão", value="E M E I F PA RESSACA")
            new_user = st.text_input("Escolha um Usuário")
            new_pass = st.text_input("Escolha uma Senha", type="password")
            btn_criar = st.form_submit_button("SOLICITAR ACESSO")
            
            if btn_criar and new_user and new_pass and new_email:
                with st.spinner("Registrando..."):
                    db_users, sha = carregar_json(ARQ_USERS)
                    lista = db_users.get("users", [])
                    
                    # Verifica duplicidade
                    if any(u['username'] == new_user for u in lista):
                        st.error("Este usuário já existe.")
                    else:
                        novo_usuario = {
                            "username": new_user,
                            "password": hash_senha(new_pass),
                            "name": new_name,
                            "email": new_email,
                            "role": "user", # Padrão é usuário comum
                            "status": "pending", # Padrão é pendente
                            "unit": new_unit
                        }
                        lista.append(novo_usuario)
                        db_users['users'] = lista
                        
                        if salvar_json(ARQ_USERS, db_users, sha, f"Novo registro: {new_user}"):
                            # Tenta enviar e-mail
                            msg_email = f"Olá {new_name},\n\nSeu cadastro no {NOME_ESCOLA} foi recebido!\nUsuário: {new_user}\nSituação: PENDENTE DE APROVAÇÃO.\n\nAguarde o administrador liberar seu acesso."
                            enviar_email(new_email, "Cadastro Recebido - Aguardando Aprovação", msg_email)
                            
                            st.success("✅ Solicitação enviada! Verifique seu e-mail. Aguarde a liberação do Admin.")
                        else:
                            st.error("Erro ao salvar no banco de dados.")

if not st.session_state['user_info']:
    tela_login()
    st.stop()

# =============================================================================
# ÁREA LOGADA
# =============================================================================

usuario = st.session_state['user_info']

# --- SIDEBAR COM O PERFIL ESTILO "CARD FLUTUANTE" ---
with st.sidebar:
    st.image(LOGO_URL, width=120)
    
    # HTML DO CARD DE PERFIL (IGUAL FOTO)
    html_perfil = f"""
    <div class="profile-container">
        <div>👤 <strong>{usuario['username']}</strong> (Passe o mouse)</div>
        <div class="profile-popup">
            <div class="profile-header">Usuário</div>
            <div style="display: flex; align-items: center;">
                <div style="flex: 1;">
                    <div class="profile-row"><span class="profile-label">NOME:</span> {usuario['name']}</div>
                    <div class="profile-row"><span class="profile-label">EMAIL:</span> {usuario['email']}</div>
                    <div class="profile-row"><span class="profile-label">PERFIL:</span> {usuario['role'].upper()}</div>
                    <div class="profile-row"><span class="profile-label">UN. PADRÃO:</span> <span style="color: blue;">{usuario.get('unit', 'Geral')}</span></div>
                </div>
                <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" width="60" style="border-radius: 50%;">
            </div>
        </div>
    </div>
    """
    st.markdown(html_perfil, unsafe_allow_html=True)
    
    # Menu de Navegação
    from streamlit_option_menu import option_menu
    
    opcoes = ["Dashboard", "Pesquisar", "Cadastrar"]
    icones = ["house", "search", "plus-circle"]
    
    # Se for ADMIN, adiciona opção extra
    if usuario['role'] == 'admin':
        opcoes.append("Administração")
        icones.append("gear")
        
    escolha = option_menu("Menu", opcoes, icons=icones, default_index=0)
    
    if st.button("Sair"):
        st.session_state['user_info'] = None
        st.rerun()

# --- CARREGA DADOS DO WORD PARA AS TELAS ---
def get_word_data():
    # (Mesma lógica de antes, resumida)
    # ... aqui você pode manter sua lógica de carregar Word ...
    return pd.DataFrame(), None, None # Placeholder para não ficar gigante o código

# --- TELA DE ADMINISTRAÇÃO ---
if escolha == "Administração" and usuario['role'] == 'admin':
    st.title("⚙️ Painel Administrativo")
    
    admin_tab1, admin_tab2 = st.tabs(["👥 Gerenciar Usuários", "🎨 Configurações do Sistema"])
    
    # 1. GERENCIAR USUÁRIOS
    with admin_tab1:
        st.subheader("Usuários do Sistema")
        
        db_users, sha_users = carregar_json(ARQ_USERS)
        users_list = db_users.get("users", [])
        
        # Converte para DataFrame para exibir bonito
        if users_list:
            df_users = pd.DataFrame(users_list)
            # Editor de dados interativo
            edited_df = st.data_editor(
                df_users,
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status", options=["active", "pending", "disabled"], required=True
                    ),
                    "role": st.column_config.SelectboxColumn(
                        "Função", options=["user", "admin"], required=True
                    ),
                    "password": st.column_config.Column("Senha (Hash)", disabled=True)
                },
                hide_index=True,
                key="editor_users"
            )
            
            if st.button("💾 Salvar Alterações de Usuários"):
                # Converte o DF editado de volta para lista
                novos_dados = edited_df.to_dict('records')
                db_users['users'] = novos_dados
                
                if salvar_json(ARQ_USERS, db_users, sha_users, "Admin atualizou usuários"):
                    # Verifica se alguém foi ativado para mandar email
                    st.success("Usuários atualizados com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Erro ao salvar.")
        else:
            st.info("Nenhum usuário encontrado.")

    # 2. CONFIGURAÇÕES VISUAIS
    with admin_tab2:
        st.subheader("Personalização")
        
        with st.form("config_form"):
            novo_nome = st.text_input("Nome do Sistema", value=NOME_ESCOLA)
            nova_cor = st.color_picker("Cor do Tema", value=COR_TEMA)
            nova_logo = st.text_input("URL da Logo", value=LOGO_URL)
            
            if st.form_submit_button("Aplicar Configurações"):
                novo_conf = {
                    "school_name": novo_nome,
                    "theme_color": nova_cor,
                    "logo_url": nova_logo
                }
                # Carrega SHA atualizado
                _, sha_conf = carregar_json(ARQ_CONFIG)
                
                if salvar_json(ARQ_CONFIG, novo_conf, sha_conf, "Atualizou config"):
                    st.success("Configurações salvas! Atualize a página para ver as mudanças.")
                else:
                    st.error("Erro ao salvar config.")

# --- OUTRAS TELAS (Dashboard, Pesquisa, etc) ---
elif escolha == "Dashboard":
    st.title(f"Bem-vindo, {usuario['name']}")
    st.info("Use o menu lateral para navegar.")
    # Coloque aqui seus gráficos...

elif escolha == "Pesquisar":
    st.title("Pesquisa de Alunos")
    # Coloque aqui sua lógica de pesquisa...

elif escolha == "Cadastrar":
    st.title("Matrícula")
    # Coloque aqui sua lógica de cadastro...

elif escolha == "Administração":
    st.error("Acesso Negado.")
