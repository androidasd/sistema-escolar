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

# --- CSS PREMIUM ---
st.markdown(f"""
<style>
    :root {{ --primary-color: {COR_TEMA}; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}}
    
    /* Centralizar Abas de Login */
    .stTabs [data-baseweb="tab-list"] {{
        justify-content: center;
    }}
    
    /* Botões Premium */
    div.stButton > button:first-child {{
        background-color: {COR_TEMA}; 
        color: white; 
        border-radius: 8px; 
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        transition: all 0.3s;
    }}
    div.stButton > button:first-child:hover {{
        opacity: 0.8;
        transform: scale(1.02);
    }}

    /* Card de Login */
    .block-container {{ padding-top: 2rem; }}
    
    /* Card de Perfil */
    .profile-container {{
        padding: 15px; 
        border-left: 5px solid {COR_TEMA};
        margin-bottom: 20px; 
        background: white; 
        border-radius: 8px; 
        cursor: pointer;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .profile-popup {{
        display: none; position: absolute; top: 0; left: 105%; width: 280px;
        background: white; border: 1px solid #eee; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); z-index: 999; border-radius: 10px;
    }}
    .profile-container:hover .profile-popup {{ display: block; }}
</style>
""", unsafe_allow_html=True)

# --- LÓGICA DE SESSÃO ---
if 'user_info' not in st.session_state: st.session_state['user_info'] = None

# --- TELA DE LOGIN ---
if not st.session_state['user_info']:
    # Layout de colunas para centralizar o card
    col_esq, col_centro, col_dir = st.columns([1, 1.2, 1])
    
    with col_centro:
        st.write("") # Espaço
        with st.container(border=True):
            # Cabeçalho do Card
            cc1, cc2 = st.columns([1, 4])
            with cc1: st.image(LOGO_URL, width=60)
            with cc2: st.markdown(f"<h3 style='margin:15px 0 0 0; color:{COR_TEMA}'>{NOME_ESCOLA}</h3>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # ABAS CENTRALIZADAS (Login via EMAIL)
            tab1, tab2 = st.tabs(["🔐 ENTRAR", "📝 CRIAR CONTA"])
            
            with tab1:
                with st.form("login_email"):
                    email_login = st.text_input("E-mail Cadastrado")
                    senha_login = st.text_input("Senha", type="password")
                    
                    if st.form_submit_button("ACESSAR SISTEMA", use_container_width=True):
                        # 1. Checa Admin Mestre (via Secrets)
                        try:
                            s_mestra = st.secrets["SENHA_SISTEMA"]
                        except: s_mestra = "admin"
                        
                        # Login de Admin Mestre (Email fixo ou qualquer um com a senha mestra)
                        if email_login.lower() == "admin" and senha_login == s_mestra:
                             st.session_state['user_info'] = {
                                 "username": "Super Admin", "name": "Administrador Geral", 
                                 "role": "admin", "email": "admin@sistema", "unit": "DIRETORIA"
                             }
                             st.rerun()
                        
                        # 2. Checa Banco de Usuários (JSON)
                        db, _ = carregar_json(ARQ_USERS)
                        users = db.get("users", [])
                        
                        # Busca usuário pelo EMAIL
                        found = next((x for x in users if x.get('email', '').lower() == email_login.lower() and x['password'] == hash_senha(senha_login)), None)
                        
                        if found:
                            if found.get('status') == 'active':
                                st.session_state['user_info'] = found
                                st.rerun()
                            else: st.warning("🔒 Conta em análise. Aguarde aprovação.")
                        else: st.error("❌ E-mail ou senha incorretos.")

            with tab2:
                with st.form("registro"):
                    st.caption("Preencha para solicitar acesso:")
                    nome_reg = st.text_input("Nome Completo")
                    email_reg = st.text_input("E-mail (Será seu Login)")
                    senha_reg = st.text_input("Crie uma Senha", type="password")
                    
                    if st.form_submit_button("SOLICITAR CADASTRO", use_container_width=True):
                        if not email_reg or "@" not in email_reg:
                            st.error("Digite um e-mail válido.")
                        else:
                            db, sha = carregar_json(ARQ_USERS)
                            lst = db.get("users", [])
                            
                            # Verifica se email já existe
                            if any(x.get('email', '').lower() == email_reg.lower() for x in lst):
                                st.error("⚠️ Este e-mail já possui cadastro.")
                            else:
                                with st.spinner("Enviando solicitação..."):
                                    # Cria novo usuário (usa email como ID e username para compatibilidade)
                                    novo_user = {
                                        "username": email_reg.split("@")[0], # Gera um user interno
                                        "password": hash_senha(senha_reg),
                                        "name": nome_reg,
                                        "email": email_reg,
                                        "role": "user",
                                        "status": "pending",
                                        "unit": "PADRÃO"
                                    }
                                    
                                    lst.append(novo_user)
                                    if not db: db = {"users": []}
                                    db['users'] = lst
                                    salvar_json(ARQ_USERS, db, sha, f"Novo registro: {email_reg}")
                                    
                                    sucesso, msg_erro = enviar_email_boas_vindas(email_reg, nome_reg)
                                    
                                    if sucesso:
                                        st.success(f"✅ Solicitação enviada! Verifique seu e-mail: {email_reg}")
                                    else:
                                        st.warning(f"⚠️ Salvo, mas erro no envio de e-mail: {msg_erro}")
    st.stop()

# --- ÁREA LOGADA ---
user = st.session_state['user_info']

# Sidebar
with st.sidebar:
    st.image(LOGO_URL, width=90)
    st.markdown(f"""
    <div class="profile-container">
        <small>Logado como:</small><br>
        <strong>{user['name']}</strong>
        <div class="profile-popup">
            <strong>E-mail:</strong> {user.get('email')}<br>
            <strong>Nível:</strong> <span style="color:{COR_TEMA}">{user['role'].upper()}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    from streamlit_option_menu import option_menu
    opts = ["Dashboard", "Pesquisar", "Cadastrar Aluno"]
    icons = ["house", "search", "person-plus"]
    if user['role'] == 'admin':
        opts.append("Administração"); icons.append("gear")
    
    menu = option_menu("Navegação", opts, icons=icons, default_index=0)
    st.divider()
    if st.button("🔒 Sair do Sistema", use_container_width=True):
        st.session_state['user_info'] = None
        st.rerun()

# --- LÓGICA DE DADOS ---
if menu in ["Dashboard", "Pesquisar"]:
    df = pd.DataFrame(carregar_dados_word())

# --- TELAS ---

if menu == "Administração":
    # DESIGN PREMIUM DO ADMIN
    st.markdown(f"## ⚙️ Administração do Sistema")
    st.info("Painel de controle de usuários e configurações.")
    
    tab_u, tab_p, tab_c = st.tabs(["👥 Gestão de Usuários", "🔑 Alterar Senhas", "🎨 Aparência"])
    
    # TAB 1: GESTÃO (STATUS E PERMISSÕES)
    with tab_u:
        db, sha = carregar_json(ARQ_USERS)
        users_list = db.get("users", [])
        
        if users_list:
            # Métricas no topo
            col_m1, col_m2 = st.columns(2)
            total_users = len(users_list)
            pending_users = len([u for u in users_list if u.get('status') == 'pending'])
            
            col_m1.metric("Total de Usuários", total_users)
            col_m2.metric("Pendentes de Aprovação", pending_users, delta_color="inverse")
            
            st.markdown("### Tabela de Usuários")
            
            # Editor de Dados
            df_users = pd.DataFrame(users_list)
            # Esconde colunas sensíveis ou técnicas
            cols_to_show = ["name", "email", "status", "role", "unit"]
            
            # Garante que as colunas existem antes de filtrar
            df_display = df_users[[c for c in cols_to_show if c in df_users.columns]]
            
            edited = st.data_editor(
                df_display,
                key="user_editor",
                use_container_width=True,
                column_config={
                    "name": "Nome",
                    "email": "E-mail (Login)",
                    "status": st.column_config.SelectboxColumn("Status", options=["active", "pending", "disabled"], help="Active=Liberado"),
                    "role": st.column_config.SelectboxColumn("Nível", options=["user", "admin"]),
                    "unit": "Unidade"
                }
            )
            
            if st.button("💾 Salvar Alterações de Status/Permissão"):
                # Atualiza a lista original com as edições (mesclando dados)
                # Lógica: O data_editor retorna um DF. Convertemos para dict e atualizamos o JSON principal mantendo as senhas originais
                novos_dados = edited.to_dict('records')
                
                # Reconstrói a lista completa preservando senhas e usernames antigos
                lista_atualizada = []
                for novo in novos_dados:
                    # Encontra o original pelo email
                    original = next((u for u in users_list if u.get('email') == novo['email']), None)
                    if original:
                        original.update(novo) # Atualiza campos editados
                        lista_atualizada.append(original)
                    else:
                        lista_atualizada.append(novo) # Caso raro de novo
                
                db['users'] = lista_atualizada
                salvar_json(ARQ_USERS, db, sha, "Admin atualizou usuários")
                st.success("✅ Banco de dados atualizado com sucesso!")
                time.sleep(1.5); st.rerun()

    # TAB 2: ALTERAR SENHAS (NOVO)
    with tab_p:
        st.markdown("### 🔐 Redefinir Senha de Usuário")
        st.warning("Use esta área para trocar a senha de um usuário que esqueceu.")
        
        db, sha = carregar_json(ARQ_USERS)
        users_list = db.get("users", [])
        
        # Selectbox com E-mails
        emails = [u.get('email') for u in users_list]
        user_selecionado = st.selectbox("Selecione o Usuário para alterar a senha:", [""] + emails)
        
        if user_selecionado:
            nova_senha_admin = st.text_input(f"Nova Senha para {user_selecionado}", type="password")
            confirmar_senha = st.text_input("Confirme a Nova Senha", type="password")
            
            if st.button("Confirmar Alteração de Senha"):
                if nova_senha_admin and nova_senha_admin == confirmar_senha:
                    # Atualiza no JSON
                    for u in users_list:
                        if u.get('email') == user_selecionado:
                            u['password'] = hash_senha(nova_senha_admin)
                            break
                    
                    db['users'] = users_list
                    if salvar_json(ARQ_USERS, db, sha, f"Admin alterou senha de {user_selecionado}"):
                        st.success(f"✅ Senha de {user_selecionado} alterada com sucesso!")
                    else:
                        st.error("Erro ao salvar.")
                else:
                    st.error("As senhas não coincidem ou estão vazias.")

    # TAB 3: CONFIGURAÇÃO
    with tab_c:
        st.markdown("### 🎨 Personalização")
        with st.form("conf_form"):
            cn = st.text_input("Nome da Escola", NOME_ESCOLA)
            cc = st.color_picker("Cor Principal (Tema)", COR_TEMA)
            cl = st.text_input("URL da Logo", LOGO_URL)
            
            if st.form_submit_button("Aplicar Novo Design"):
                _, s_c = carregar_json(ARQ_CONFIG)
                salvar_json(ARQ_CONFIG, {"school_name": cn, "theme_color": cc, "logo_url": cl}, s_c, "Update config")
                st.toast("Design atualizado! Atualizando página..."); time.sleep(2); st.rerun()

elif menu == "Dashboard":
    st.markdown(f"## 📊 Visão Geral")
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("Total de Alunos", len(df))
        with col2: st.metric("Concluintes", len(df[df['Categoria']=="Concluinte"]))
        with col3: st.metric("Passivos", len(df[df['Categoria']=="Passivo"]))
        
        st.markdown("### Últimos Cadastros")
        st.dataframe(df.tail(5), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum aluno encontrado na base de dados.")

elif menu == "Pesquisar":
    st.markdown("## 🔍 Consultar Aluno")
    busca = st.text_input("Nome do Aluno", placeholder="Digite para buscar...")
    if busca and not df.empty:
        res = df[df['Nome'].str.contains(busca.upper(), na=False)]
        if not res.empty:
            st.success(f"{len(res)} alunos encontrados.")
            st.dataframe(res, use_container_width=True, hide_index=True)
        else: st.warning("Nenhum aluno encontrado.")
    elif not busca: st.info("Digite o nome acima para ver os resultados.")

elif menu == "Cadastrar Aluno":
    st.markdown("## 📝 Novo Aluno")
    with st.container(border=True):
        with st.form("novo_aluno"):
            c1, c2 = st.columns([1,4])
            num = c1.text_input("Nº (Ex: 105)")
            nome = c2.text_input("Nome Completo")
            tipo = st.radio("Lista de Destino", ["Passivos", "Concluintes"], horizontal=True)
            obs = st.text_input("Observação")
            
            if st.form_submit_button("💾 SALVAR ALUNO NO SISTEMA", use_container_width=True):
                arq = ARQ_PASSIVOS if tipo == "Passivos" else ARQ_CONCLUINTES
                if not num: num = "S/N"
                if salvar_aluno_word(arq, num, nome, obs):
                    st.balloons()
                    st.success(f"✅ Aluno {nome} salvo com sucesso!")
                    time.sleep(1); st.cache_data.clear(); st.rerun()
                else: st.error("Erro ao salvar no GitHub.")
