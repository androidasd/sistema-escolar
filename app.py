import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão Escolar", page_icon="🔒", layout="wide")

# --- ESTILO VISUAL ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00A8C6;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

def verificar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Digite a senha administrativa para acessar o sistema.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        senha_digitada = st.text_input("Senha:", type="password")
        if st.button("ENTRAR NO SISTEMA", use_container_width=True):
            # Compara com a senha salva nos Secrets
            if senha_digitada == st.secrets["SENHA_SISTEMA"]:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("🚫 Senha incorreta!")

# SE NÃO ESTIVER LOGADO, MOSTRA SÓ A TELA DE LOGIN E PARA TUDO
if not st.session_state['logado']:
    verificar_login()
    st.stop() # Importante: O código para de ler aqui se não tiver senha

# ==============================================================================
# DAQUI PARA BAIXO É O SEU SISTEMA (SÓ CARREGA SE TIVER LOGADO)
# ==============================================================================

# Tenta importar bibliotecas visuais
try:
    import plotly.express as px
    from streamlit_option_menu import option_menu
    tem_visuais = True
except:
    tem_visuais = False

# --- CONEXÃO GITHUB AUTOMÁTICA ---
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
        if repos:
            repo_ref = repos[0]

    if not repo_ref:
        st.error("❌ Repositório não encontrado.")
        st.stop()
        
except Exception as e:
    st.error(f"⚙️ Erro de Conexão: {e}")
    st.stop()

ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

# --- FUNÇÕES ---

@st.cache_data(ttl=60)
def carregar_dados_simples():
    """Lê os arquivos Word incluindo a NUMERAÇÃO"""
    def ler_arquivo(nome_arq, categoria):
        local = []
        try:
            conteudo = repo_ref.get_contents(nome_arq)
            doc = Document(io.BytesIO(conteudo.decoded_content))
            sha = conteudo.sha
            
            for tabela in doc.tables:
                for linha in tabela.rows:
                    if len(linha.cells) >= 2:
                        numero = linha.cells[0].text.strip()
                        nome = linha.cells[1].text.strip().upper()
                        obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                        if len(nome) > 3 and "NOME" not in nome:
                            local.append({
                                "Numero": numero,
                                "Nome": nome, 
                                "Categoria": categoria, 
                                "Obs": obs
                            })
            return local, sha
        except:
            return [], None

    l_p, sha_p = ler_arquivo(ARQ_PASSIVOS, "Passivo")
    l_c, sha_c = ler_arquivo(ARQ_CONCLUINTES, "Concluinte")
    
    return l_p + l_c, sha_p, sha_c

def salvar_github(arquivo, numero_novo, nome, obs):
    try:
        conteudo = repo_ref.get_contents(arquivo)
        doc = Document(io.BytesIO(conteudo.decoded_content))
        
        if len(doc.tables) > 0:
            tab = doc.tables[0]
            row = tab.add_row()
            row.cells[0].text = numero_novo 
            row.cells[1].text = nome.upper()
            if len(row.cells) > 2:
                row.cells[2].text = obs
            
            buffer = io.BytesIO()
            doc.save(buffer)
            repo_ref.update_file(arquivo, f"Add: {nome}", buffer.getvalue(), conteudo.sha)
            return True
    except:
        return False
    return False

# --- CARREGAMENTO ---
dados, sha_p, sha_c = carregar_dados_simples()
df = pd.DataFrame(dados)

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🏫 Menu")
    if tem_visuais:
        escolha = option_menu(
            menu_title=None,
            options=["Dashboard", "Pesquisar", "Cadastrar"],
            icons=["house", "search", "plus-circle"],
            default_index=0,
        )
    else:
        escolha = st.radio("Menu", ["Dashboard", "Pesquisar", "Cadastrar"])

    st.divider()
    # BOTÃO DE SAIR (LOGOUT)
    if st.button("🔒 Sair do Sistema"):
        st.session_state['logado'] = False
        st.rerun()

# --- TELAS ---

if escolha == "Dashboard":
    st.title("📊 Visão Geral")
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total", len(df))
        c2.metric("Concluintes", len(df[df['Categoria']=="Concluinte"]))
        c3.metric("Passivos", len(df[df['Categoria']=="Passivo"]))
        
        st.divider()
        if tem_visuais:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Categorias")
                fig = px.pie(df, names='Categoria', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                st.subheader("Últimos Cadastros")
                if "Numero" in df.columns:
                    st.dataframe(df.tail(5)[['Numero', 'Nome']], hide_index=True)
                else:
                    st.dataframe(df.tail(5), hide_index=True)
        else:
            st.dataframe(df.tail(10), use_container_width=True)

if escolha == "Pesquisar":
    st.title("🔍 Buscar Aluno")
    busca = st.text_input("Digite o nome do aluno:", placeholder="Ex: Maria...")
    
    if busca:
        if not df.empty:
            df_show = df[df['Nome'].str.contains(busca.upper(), na=False)]
            if not df_show.empty:
                st.success(f"{len(df_show)} registros encontrados.")
                st.dataframe(
                    df_show, 
                    use_container_width=True, 
                    height=500,
                    column_config={
                        "Numero": st.column_config.TextColumn("Nº", width="small"),
                        "Nome": st.column_config.TextColumn("Nome Completo"),
                        "Categoria": st.column_config.TextColumn("Status"),
                        "Obs": st.column_config.TextColumn("Observações"),
                    },
                    hide_index=True
                )
            else:
                st.warning("Nenhum aluno encontrado.")
    else:
        st.info("👆 Digite um nome acima para pesquisar.")

if escolha == "Cadastrar":
    st.title("📝 Nova Matrícula")
    st.info("Preencha os dados abaixo.")
    
    with st.form("novo"):
        col1, col2 = st.columns([1, 4])
        with col1:
            num_novo = st.text_input("Nº (Ex: 018)", placeholder="000")
        with col2:
            nome = st.text_input("Nome Completo:")
            
        tipo = st.radio("Lista de Destino:", ["Concluintes", "Passivos"])
        obs = st.text_input("Observação (Opcional):")
        
        if st.form_submit_button("💾 Salvar Aluno"):
            if not num_novo: num_novo = "S/N"
            arq = ARQ_CONCLUINTES if tipo == "Concluintes" else ARQ_PASSIVOS
            with st.spinner("Salvando..."):
                if salvar_github(arq, num_novo, nome, obs):
                    st.success(f"Aluno {nome} salvo!")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Erro ao salvar.")
