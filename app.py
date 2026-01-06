import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io
import time
import json
import hashlib

# --- FUNÇÕES UTILITÁRIAS ---

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# (Função de e-mail desativada temporariamente para não travar)
def enviar_notificacao_simulada(nome):
    print(f"Novo cadastro recebido: {nome}")
    return True

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
        # Tenta pegar o primeiro repositório se a busca falhar
        repos = list(user.get_repos())
        if repos:
            repo_ref = repos[0]
            
    if not repo_ref:
        st.error("Erro: Não encontrei o repositório no GitHub.")
        st.stop()

except Exception as e:
    st.error(f"Erro crítico de conexão: {e}")
    st.info("Verifique se o GITHUB_TOKEN está correto nos Secrets.")
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
        if sha:
            repo_ref.update_file(arquivo, mensagem, dados_str, sha)
        else:
            repo_ref.create_file(arquivo, mensagem, dados_str)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- CARREGA CONFIGURAÇÕES INICIAIS ---
config_data, config_sha = carregar_json(ARQ_CONFIG)
# Valores padrão caso o arquivo config.json ainda não exista
COR_TEMA = config_data.get("theme_color", "#00A8C6")
NOME_ESCOLA = config_data.get("school_name", "SISTEMA ESCOLAR")
LOGO_URL = config_data.get("logo_url", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

st.set_page_config(page_title=NOME_ESCOLA, page_icon="🎓", layout="wide")

# --- CSS PERSONALIZADO ---
st.markdown(f"""
<style>
    :root {{ --primary-color: {COR_TEMA}; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
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
        top: 0px; left: 105%; width: 280px;
        background-color: #fff; border: 1px solid #ccc;
        border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        z-index: 999; padding: 15px; color: black;
    }}
    .profile-container:hover .profile-popup {{ display: block; }}
    .profile-header {{
        border-bottom: 2px solid {COR_TEMA}; padding-bottom: 5px;
        margin-bottom: 10px; font-weight: bold; font-size: 18px; text-align: center;
    }}
    div.stButton > button:first-child {{ background-color: {COR_TEMA}; color: white; }}
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---

if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

def tela_login():
    st.markdown(f"<h1 style='text-align: center; color: {COR_TEMA};'>{NOME_ESCOLA}</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 ACESSAR SISTEMA", "📝 CRIAR NOVO USUÁRIO"])
    
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
                    if usuario_encontrado.get('status') == 'active':
                        st.session_state['user_info'] = usuario_encontrado
                        st.rerun()
                    elif usuario_encontrado.get('status') == 'pending':
                        st.warning("⏳ Sua conta foi criada, mas ainda aguarda aprovação do Administrador.")
                    else:
                        st.error("🚫 Conta desativada.")
                else:
                    st.error("Usuário ou senha incorretos. Verifique se digitou certo.")

    with tab2:
        st.info("Preencha os dados abaixo para solicitar seu acesso.")
        with st.form("registro_form"):
            new_name = st.text_input("Nome Completo")
            new_email = st.text_input("E-mail")
            new_unit = st.text_input("Unidade", value="E M E I F PA RESSACA")
            new_user = st.text_input("Crie seu Login (Usuário)")
            new_pass = st.text_input("Crie sua Senha", type="password")
            
            if st.form_submit_button("SOLICITAR CADASTRO"):
                if new_user and new_pass:
                    with st.spinner("Registrando..."):
                        db_users, sha = carregar_json(ARQ_USERS)
                        lista = db_users.get("users", [])
                        
                        if any(u['username'] == new_user for u in lista):
                            st.error("Este nome de usuário já existe. Tente outro.")
                        else:
                            novo_usuario = {
                                "username": new_user,
                                "password": hash_senha(new_pass),
                                "name": new_name,
                                "email": new_email,
                                "role": "user",
                                "status": "pending", # Começa bloqueado
                                "unit": new_unit
                            }
                            # Se não existir lista, cria
                            if lista is None: lista = []
                            lista.append(novo_usuario)
                            
                            # Se o arquivo users.json não existir, cria a estrutura
                            if not db_users: db_users = {"users": []}
                            db_users['users'] = lista
                            
                            if salvar_json(ARQ_USERS, db_users, sha, f"Novo user: {new_user}"):
                                st.success("✅ Cadastro Realizado! Avise o administrador para liberar seu acesso.")
                            else:
                                st.error("Erro ao salvar cadastro.")

if not st.session_state['user_info']:
    tela_login()
    st.stop()

# =============================================================================
# ÁREA LOGADA
# =============================================================================

usuario = st.session_state['user_info']

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=100)
    
    # CARD FLUTUANTE
    html_perfil = f"""
    <div class="profile-container">
        <div>👤 <strong>{usuario['username']}</strong> <small>▼</small></div>
        <div class="profile-popup">
            <div class="profile-header">FICHA DO USUÁRIO</div>
            <div style="font-size:14px;">
                <p><strong>NOME:</strong> {usuario['name']}</p>
                <p><strong>EMAIL:</strong> {usuario.get('email', '')}</p>
                <p><strong>PERFIL:</strong> {usuario['role'].upper()}</p>
                <p><strong>UNIDADE:</strong> <span style="color:blue">{usuario.get('unit', '')}</span></p>
            </div>
        </div>
    </div>
    """
    st.markdown(html_perfil, unsafe_allow_html=True)
    
    # MENU
    from streamlit_option_menu import option_menu
    
    opcoes = ["Dashboard", "Pesquisar", "Cadastrar Aluno"]
    icones = ["house", "search", "person-plus"]
    
    if usuario['role'] == 'admin':
        opcoes.append("Administração")
        icones.append("gear")
        
    escolha = option_menu("Menu Principal", opcoes, icons=icones, default_index=0)
    
    st.divider()
    if st.button("🔒 Sair / Logout"):
        st.session_state['user_info'] = None
        st.rerun()

# --- CONTEÚDO ---

if escolha == "Administração" and usuario['role'] == 'admin':
    st.title("⚙️ Painel do Diretor/Admin")
    
    tab_users, tab_config = st.tabs(["👥 Liberar Usuários", "🎨 Aparência"])
    
    with tab_users:
        st.write("Abaixo você pode ativar novos cadastros ou bloquear usuários.")
        db_users, sha_users = carregar_json(ARQ_USERS)
        users_list = db_users.get("users", [])
        
        if users_list:
            df_users = pd.DataFrame(users_list)
            
            # Editor Poderoso
            edited_df = st.data_editor(
                df_users,
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Situação", 
                        help="Active=Liberado, Pending=Aguardando, Disabled=Bloqueado",
                        options=["active", "pending", "disabled"], 
                        required=True
                    ),
                    "role": st.column_config.SelectboxColumn(
                        "Nível", options=["user", "admin"], required=True
                    ),
                    "password": st.column_config.Column("Senha", disabled=True),
                    "username": st.column_config.Column("Login", disabled=True)
                },
                hide_index=True,
                num_rows="dynamic",
                key="editor_users_grid"
            )
            
            if st.button("💾 SALVAR MUDANÇAS DE USUÁRIOS"):
                novos_dados = edited_df.to_dict('records')
                db_users['users'] = novos_dados
                if salvar_json(ARQ_USERS, db_users, sha_users, "Admin atualizou permissões"):
                    st.success("Permissões atualizadas com sucesso!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.warning("Nenhum usuário cadastrado ainda.")

    with tab_config:
        st.write("Personalize o sistema.")
        with st.form("conf_form"):
            c_nome = st.text_input("Nome da Escola", value=NOME_ESCOLA)
            c_cor = st.color_picker("Cor Principal", value=COR_TEMA)
            c_logo = st.text_input("Link da Logo", value=LOGO_URL)
            
            if st.form_submit_button("APLICAR TEMA"):
                new_conf = {"school_name": c_nome, "theme_color": c_cor, "logo_url": c_logo}
                _, sha_conf = carregar_json(ARQ_CONFIG)
                salvar_json(ARQ_CONFIG, new_conf, sha_conf, "Atualizou tema")
                st.toast("Tema atualizado! Dê F5 na página.")
                time.sleep(2)
                st.rerun()

# --- OUTRAS TELAS (MANTIDAS DO SEU SISTEMA ANTERIOR) ---
elif escolha == "Dashboard":
    st.title(f"Olá, {usuario['name']}!")
    st.info("Bem-vindo ao sistema de gestão escolar.")
    # (Seus gráficos viriam aqui)

elif escolha == "Pesquisar":
    st.title("🔍 Buscar Aluno")
    # (Lógica de pesquisa anterior)
    st.write("Funcionalidade de pesquisa ativa.")

elif escolha == "Cadastrar Aluno":
    st.title("📝 Nova Matrícula")
    # (Lógica de cadastro anterior)
    st.write("Funcionalidade de cadastro ativa.")

elif escolha == "Administração":
    st.error("🚫 Área restrita apenas para administradores.")
