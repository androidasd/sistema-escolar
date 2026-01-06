import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io
import time

# Tenta importar as bibliotecas visuais. Se der erro, avisa amigavelmente.
try:
    import plotly.express as px
    from streamlit_option_menu import option_menu
except ImportError:
    st.error("⚠️ ERRO DE INSTALAÇÃO: Faltam bibliotecas no requirements.txt")
    st.info("Adicione 'plotly' e 'streamlit-option-menu' no seu arquivo requirements.txt no GitHub.")
    st.stop()

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gestão Escolar", page_icon="🎓", layout="wide")

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

# --- CONEXÃO GITHUB AUTOMÁTICA ---
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    g = Github(TOKEN)
    user = g.get_user()
    
    # LÓGICA INTELIGENTE: Pega o primeiro repositório que tiver "sistema" ou "alunos" no nome
    repo_ref = None
    repos_encontrados = []
    
    for repo in user.get_repos():
        repos_encontrados.append(repo.name)
        # Verifica palavras chaves comuns
        if "sistema" in repo.name.lower() or "alunos" in repo.name.lower() or "emeif" in repo.name.lower():
            repo_ref = repo
            break
            
    # Se não achou por nome, tenta pegar o último atualizado (fallback)
    if not repo_ref and repos_encontrados:
        repo_ref = user.get_repo(repos_encontrados[0])

    if not repo_ref:
        st.error(f"❌ Não encontrei nenhum repositório. Repositórios na sua conta: {repos_encontrados}")
        st.stop()
        
except Exception as e:
    st.error(f"⚙️ Erro de Conexão com GitHub: {e}")
    st.info("Verifique se o Token está colado corretamente nos Secrets do Streamlit.")
    st.stop()

ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

# --- FUNÇÕES ---

@st.cache_data(ttl=60)
def carregar_dados_simples():
    """Lê os arquivos Word e retorna apenas listas de nomes (sem travar o cache)"""
    lista_completa = []
    
    def processar_arquivo(nome_arquivo, categoria):
        local_lista = []
        try:
            # Pega o arquivo do GitHub
            file_content = repo_ref.get_contents(nome_arquivo)
            # Abre o Word na memória
            doc = Document(io.BytesIO(file_content.decoded_content))
            sha = file_content.sha
            
            for tabela in doc.tables:
                for linha in tabela.rows:
                    if len(linha.cells) >= 2:
                        nome = linha.cells[1].text.strip().upper()
                        obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                        if len(nome) > 3 and "NOME" not in nome:
                            local_lista.append({"Nome": nome, "Categoria": categoria, "Obs": obs})
            return local_lista, sha
        except:
            return [], None

    l_passivos, sha_p = processar_arquivo(ARQ_PASSIVOS, "Passivo")
    l_concluintes, sha_c = processar_arquivo(ARQ_CONCLUINTES, "Concluinte")
    
    return l_passivos + l_concluintes, sha_p, sha_c

def salvar_no_github(arquivo_alvo, nome, obs):
    try:
        contents = repo_ref.get_contents(arquivo_alvo)
        doc = Document(io.BytesIO(contents.decoded_content))
        
        if len(doc.tables) > 0:
            tab = doc.tables[0]
            row = tab.add_row()
            row.cells[0].text = "NOVO"
            row.cells[1].text = nome.upper()
            if len(row.cells) > 2:
                row.cells[2].text = obs
            
            buffer = io.BytesIO()
            doc.save(buffer)
            repo_ref.update_file(arquivo_alvo, f"Add: {nome}", buffer.getvalue(), contents.sha)
            return True
    except:
        return False
    return False

# --- CARREGAR DADOS ---
dados, sha_p, sha_c = carregar_dados_simples()
df = pd.DataFrame(dados)

# --- MENU LATERAL ---
with st.sidebar:
    st.title("🏫 Menu Escolar")
    # Menu simples e robusto
    escolha = option_menu(
        menu_title=None,
        options=["Dashboard", "Pesquisar", "Cadastrar"],
        icons=["house", "search", "plus-circle"],
        default_index=0,
    )
    st.write(f"📁 Conectado em: **{repo_ref.name}**")
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

# --- TELAS ---

if escolha == "Dashboard":
    st.title("📊 Visão Geral")
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Alunos", len(df))
        col2.metric("Concluintes", len(df[df['Categoria']=="Concluinte"]))
        col3.metric("Passivos", len(df[df['Categoria']=="Passivo"]))
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Gráfico")
            fig = px.pie(df, names='Categoria', hole=0.4, color_discrete_sequence=['#00A8C6', '#FF6B6B'])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Últimos Cadastros")
            st.dataframe(df.tail(5)[['Nome', 'Categoria']], hide_index=True)
    else:
        st.warning("Nenhum aluno encontrado nos arquivos.")

if escolha == "Pesquisar":
    st.title("🔍 Buscar Aluno")
    busca = st.text_input("Digite o nome:")
    if not df.empty:
        df_show = df
        if busca:
            df_show = df[df['Nome'].str.contains(busca.upper(), na=False)]
        
        st.dataframe(
            df_show, 
            use_container_width=True, 
            height=500,
            column_config={
                "Nome": st.column_config.TextColumn("Nome Completo"),
                "Categoria": st.column_config.BadgeColumn("Status"),
            },
            hide_index=True
        )

if escolha == "Cadastrar":
    st.title("📝 Nova Matrícula")
    with st.form("novo"):
        nome = st.text_input("Nome:")
        tipo = st.radio("Lista:", ["Concluintes", "Passivos"])
        obs = st.text_input("Obs:")
        
        if st.form_submit_button("💾 Salvar"):
            arq = ARQ_CONCLUINTES if tipo == "Concluintes" else ARQ_PASSIVOS
            with st.spinner("Salvando..."):
                if salvar_no_github(arq, nome, obs):
                    st.success("Salvo com sucesso!")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Erro ao salvar.")
