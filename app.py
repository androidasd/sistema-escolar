import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io
import time

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

# Tenta importar bibliotecas extras, se não tiver, usa padrão
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
    
    # LÓGICA INTELIGENTE PARA ACHAR O REPOSITÓRIO
    repo_ref = None
    # 1. Tenta pelo nome exato ou parecido
    for repo in user.get_repos():
        if "sistema" in repo.name.lower() or "escolar" in repo.name.lower() or "emeif" in repo.name.lower():
            repo_ref = repo
            break
            
    # 2. Se não achou, pega o último modificado
    if not repo_ref:
        repos = list(user.get_repos())
        if repos:
            repo_ref = repos[0]

    if not repo_ref:
        st.error("❌ Não encontrei nenhum repositório no seu GitHub.")
        st.stop()
        
except Exception as e:
    st.error(f"⚙️ Erro de Conexão com GitHub: {e}")
    st.info("Verifique se o Token está nos Secrets.")
    st.stop()

ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

# --- FUNÇÕES ---

@st.cache_data(ttl=60)
def carregar_dados_simples():
    """Lê os arquivos Word e retorna lista limpa"""
    lista_final = []
    
    def ler_arquivo(nome_arq, categoria):
        local = []
        try:
            conteudo = repo_ref.get_contents(nome_arq)
            doc = Document(io.BytesIO(conteudo.decoded_content))
            sha = conteudo.sha
            
            for tabela in doc.tables:
                for linha in tabela.rows:
                    if len(linha.cells) >= 2:
                        nome = linha.cells[1].text.strip().upper()
                        obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                        if len(nome) > 3 and "NOME" not in nome:
                            local.append({"Nome": nome, "Categoria": categoria, "Obs": obs})
            return local, sha
        except:
            return [], None

    l_p, sha_p = ler_arquivo(ARQ_PASSIVOS, "Passivo")
    l_c, sha_c = ler_arquivo(ARQ_CONCLUINTES, "Concluinte")
    
    return l_p + l_c, sha_p, sha_c

def salvar_github(arquivo, nome, obs):
    try:
        conteudo = repo_ref.get_contents(arquivo)
        doc = Document(io.BytesIO(conteudo.decoded_content))
        
        if len(doc.tables) > 0:
            tab = doc.tables[0]
            row = tab.add_row()
            row.cells[0].text = "NOVO"
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

    st.caption(f"Conectado: {repo_ref.name}")
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
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
                st.subheader("Últimos")
                st.dataframe(df.tail(5), hide_index=True)
        else:
            st.dataframe(df.tail(10), use_container_width=True)

if escolha == "Pesquisar":
    st.title("🔍 Buscar Aluno")
    busca = st.text_input("Nome:")
    
    if not df.empty:
        df_show = df
        if busca:
            df_show = df[df['Nome'].str.contains(busca.upper(), na=False)]
        
        # AQUI ESTAVA O ERRO - REMOVI O 'BadgeColumn' QUE TRAVAVA
        st.dataframe(
            df_show, 
            use_container_width=True, 
            height=500,
            column_config={
                "Nome": st.column_config.TextColumn("Nome Completo"),
                "Categoria": st.column_config.TextColumn("Status"), # Corrigido para Texto Simples
                "Obs": st.column_config.TextColumn("Observações"),
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
                if salvar_github(arq, nome, obs):
                    st.success("Salvo com sucesso!")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Erro ao salvar.")
