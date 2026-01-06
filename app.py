import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io
import plotly.express as px
from streamlit_option_menu import option_menu
import time

# --- CONFIGURAÇÃO INICIAL (LAYOUT WIDE) ---
st.set_page_config(page_title="Gestão Escolar Pro", page_icon="🎓", layout="wide")

# --- ESTILO CSS PERSONALIZADO (VISUAL MODERNO) ---
st.markdown("""
<style>
    /* Remove marca d'agua e menus padrao */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Card de Metricas */
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Titulos */
    h1, h2, h3 {
        color: #0e1117;
        font-family: 'Helvetica Neue', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO GITHUB ---
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    g = Github(TOKEN)
    user = g.get_user()
    repo_ref = None
    for repo in user.get_repos():
        if "sistema-escolar" in repo.name:
            repo_ref = repo
            break
    if not repo_ref:
        st.error("❌ Repositório não encontrado.")
        st.stop()
except:
    st.error("⚙️ Configure o Token no Secrets do Streamlit.")
    st.stop()

ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

# --- FUNÇÕES DE BACKEND ---
@st.cache_data(ttl=60) # Cache para deixar rápido (atualiza a cada 60s)
def carregar_dados():
    try:
        # Carrega Passivos
        cont_p = repo_ref.get_contents(ARQ_PASSIVOS)
        doc_p = Document(io.BytesIO(cont_p.decoded_content))
        sha_p = cont_p.sha
        
        # Carrega Concluintes
        cont_c = repo_ref.get_contents(ARQ_CONCLUINTES)
        doc_c = Document(io.BytesIO(cont_c.decoded_content))
        sha_c = cont_c.sha
        
        return doc_p, sha_p, doc_c, sha_c
    except:
        return None, None, None, None

def extrair_tabela(doc, categoria):
    lista = []
    if doc:
        for tabela in doc.tables:
            for linha in tabela.rows:
                if len(linha.cells) >= 2:
                    nome = linha.cells[1].text.strip().upper()
                    obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                    if len(nome) > 3 and "NOME" not in nome:
                        lista.append({"Nome": nome, "Categoria": categoria, "Observação": obs})
    return lista

def salvar_aluno(arquivo_nome, sha_antigo, nome_aluno, obs_aluno):
    try:
        # Recarrega o arquivo atualizado para não sobrescrever
        contents = repo_ref.get_contents(arquivo_nome)
        doc = Document(io.BytesIO(contents.decoded_content))
        
        if len(doc.tables) > 0:
            tabela = doc.tables[0]
            nova_linha = tabela.add_row()
            nova_linha.cells[0].text = "NOVO"
            nova_linha.cells[1].text = nome_aluno.upper()
            if len(nova_linha.cells) > 2:
                nova_linha.cells[2].text = obs_aluno
            
            # Salva
            buffer = io.BytesIO()
            doc.save(buffer)
            repo_ref.update_file(arquivo_nome, f"Cadastrou: {nome_aluno}", buffer.getvalue(), contents.sha)
            return True
    except Exception as e:
        st.error(f"Erro: {e}")
        return False
    return False

# --- CARREGAMENTO DE DADOS ---
doc_p, sha_p, doc_c, sha_c = carregar_dados()
dados_gerais = extrair_tabela(doc_p, "Passivo") + extrair_tabela(doc_c, "Concluinte")
df = pd.DataFrame(dados_gerais)

# --- MENU LATERAL SOFISTICADO ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.title("Gestão Escolar")
    
    escolha = option_menu(
        menu_title=None,
        options=["Dashboard", "Consultar Alunos", "Nova Matrícula"],
        icons=["graph-up-arrow", "search", "person-plus-fill"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "orange", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#00A8C6"},
        }
    )
    st.divider()
    st.caption("Sistema v3.0 - Cloud Connected")

# --- PÁGINA 1: DASHBOARD (VISÃO GERAL) ---
if escolha == "Dashboard":
    st.title("📊 Painel de Controle")
    st.markdown("Visão geral dos dados escolares em tempo real.")
    
    # 1. Cartões de Métricas (KPIs)
    col1, col2, col3 = st.columns(3)
    total_alunos = len(df)
    total_concluintes = len(df[df['Categoria']=="Concluinte"])
    total_passivos = len(df[df['Categoria']=="Passivo"])
    
    col1.metric("🎓 Total de Alunos", total_alunos)
    col2.metric("✅ Concluintes", total_concluintes, delta=f"{round((total_concluintes/total_alunos)*100)}%")
    col3.metric("📂 Arquivo Passivo", total_passivos)
    
    st.divider()
    
    # 2. Gráficos Interativos (Plotly)
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Distribuição por Categoria")
        if not df.empty:
            fig = px.pie(df, names='Categoria', values=None, hole=0.4, 
                         color='Categoria',
                         color_discrete_map={'Concluinte':'#00A8C6', 'Passivo':'#FF6B6B'})
            st.plotly_chart(fig, use_container_width=True)
            
    with c2:
        st.subheader("Últimos Cadastros")
        st.dataframe(df.tail(5)[['Nome', 'Categoria']], hide_index=True)

# --- PÁGINA 2: CONSULTAR (BUSCA AVANÇADA) ---
if escolha == "Consultar Alunos":
    st.title("🔍 Banco de Dados")
    
    col_busca, col_filtro = st.columns([3, 1])
    with col_busca:
        busca = st.text_input("Pesquisar por nome:", placeholder="Digite para filtrar...")
    with col_filtro:
        filtro_cat = st.selectbox("Filtrar Tipo:", ["Todos", "Concluinte", "Passivo"])
    
    # Lógica de Filtro
    df_filtrado = df.copy()
    if filtro_cat != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Categoria'] == filtro_cat]
    
    if busca:
        df_filtrado = df_filtrado[df_filtrado['Nome'].str.contains(busca.upper(), na=False)]
    
    # Tabela Moderna
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        height=500,
        column_config={
            "Nome": st.column_config.TextColumn("Nome do Aluno", help="Nome completo"),
            "Categoria": st.column_config.BadgeColumn("Status", help="Situação escolar"),
            "Observação": st.column_config.TextColumn("Notas/Obs")
        },
        hide_index=True
    )

# --- PÁGINA 3: NOVA MATRÍCULA ---
if escolha == "Nova Matrícula":
    st.title("📝 Cadastro de Aluno")
    st.markdown("Adicione novos registros diretamente aos arquivos Word.")
    
    with st.form("form_cadastro", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            nome = st.text_input("Nome Completo")
        with col_b:
            tipo = st.selectbox("Arquivo de Destino", ["EMEF PA-RESSACA (Passivos)", "CONCLUINTES"])
            
        obs = st.text_area("Observações (Opcional)")
        
        btn_enviar = st.form_submit_button("💾 Salvar Registro", type="primary")
        
        if btn_enviar and nome:
            with st.spinner("Conectando ao servidor e gravando dados..."):
                arquivo_alvo = ARQ_CONCLUINTES if "CONCLUINTES" in tipo else ARQ_PASSIVOS
                sha_alvo = sha_c if "CONCLUINTES" in tipo else sha_p
                
                if salvar_aluno(arquivo_alvo, sha_alvo, nome, obs):
                    st.success("✅ Aluno cadastrado com sucesso!")
                    st.balloons()
                    time.sleep(2)
                    st.cache_data.clear() # Limpa o cache para atualizar a tabela
                    st.rerun()
