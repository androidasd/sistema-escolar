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
    # Procura o repositório
    for repo in user.get_repos():
        if "sistema-escolar" in repo.name:
            repo_ref = repo
            break
    if not repo_ref:
        st.error("❌ Repositório 'sistema-escolar' não encontrado.")
        st.stop()
except Exception as e:
    st.error(f"⚙️ Erro de Conexão: {e}")
    st.stop()

ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

# --- FUNÇÕES DE PROCESSAMENTO ---

def extrair_lista_do_doc(doc_bytes, categoria):
    """Transforma o arquivo Word em uma lista de dados simples"""
    lista = []
    try:
        doc = Document(io.BytesIO(doc_bytes))
        for tabela in doc.tables:
            for linha in tabela.rows:
                if len(linha.cells) >= 2:
                    nome = linha.cells[1].text.strip().upper()
                    obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                    # Filtros para ignorar cabeçalhos
                    if len(nome) > 3 and "NOME" not in nome:
                        lista.append({"Nome": nome, "Categoria": categoria, "Observação": obs})
    except Exception as e:
        st.error(f"Erro ao ler tabela: {e}")
    return lista

# --- CACHE DE DADOS (CORRIGIDO) ---
@st.cache_data(ttl=60) 
def carregar_dados_processados():
    """Baixa e processa os dados, retornando apenas listas (que não dão erro no cache)"""
    try:
        # 1. Baixa Passivos
        cont_p = repo_ref.get_contents(ARQ_PASSIVOS)
        lista_p = extrair_lista_do_doc(cont_p.decoded_content, "Passivo")
        sha_p = cont_p.sha
        
        # 2. Baixa Concluintes
        cont_c = repo_ref.get_contents(ARQ_CONCLUINTES)
        lista_c = extrair_lista_do_doc(cont_c.decoded_content, "Concluinte")
        sha_c = cont_c.sha
        
        # Retorna listas somadas e os códigos SHA
        return lista_p + lista_c, sha_p, sha_c
    except Exception as e:
        st.error(f"Erro ao baixar do GitHub: {e}")
        return [], None, None

def salvar_aluno_github(arquivo_nome, sha_antigo, nome_aluno, obs_aluno):
    try:
        # Baixa o arquivo fresco para edição
        contents = repo_ref.get_contents(arquivo_nome)
        doc = Document(io.BytesIO(contents.decoded_content))
        
        if len(doc.tables) > 0:
            tabela = doc.tables[0]
            nova_linha = tabela.add_row()
            nova_linha.cells[0].text = "NOVO"
            nova_linha.cells[1].text = nome_aluno.upper()
            if len(nova_linha.cells) > 2:
                nova_linha.cells[2].text = obs_aluno
            
            # Salva na memória
            buffer = io.BytesIO()
            doc.save(buffer)
            # Envia para o GitHub
            repo_ref.update_file(arquivo_nome, f"Cadastrou: {nome_aluno}", buffer.getvalue(), contents.sha)
            return True
        else:
            st.error("Arquivo sem tabela para escrever.")
            return False
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
