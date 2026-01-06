import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Secretaria Escolar", page_icon="🏫", layout="wide")

# --- CONEXÃO COM GITHUB (SEGURANÇA) ---
# Pega a chave que você salvou nos "Secrets" do site
try:
    TOKEN = st.secrets["GITHUB_TOKEN"]
    g = Github(TOKEN)
    # Substitua pelo SEU usuário e nome do repositório ex: "joao/sistema-escolar"
    # O sistema tenta achar automático, mas se der erro, coloque manual
    repo_name = "seu-usuario/sistema-escolar" # <--- ATENÇÃO: O SITE VAI TENTAR DESCOBRIR SOZINHO, MAS SE DER ERRO ALTERE AQUI
    
    # Tenta descobrir o repositório atual automaticamente
    user = g.get_user()
    for repo in user.get_repos():
        if repo.name == "sistema-escolar":
            repo_ref = repo
            break
except:
    st.error("ERRO: Configure o 'GITHUB_TOKEN' nas configurações (Secrets) do Streamlit.")
    st.stop()

ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

# --- FUNÇÕES DE BANCO DE DADOS ---

def carregar_dados_github(nome_arquivo):
    """Baixa o arquivo Word direto do GitHub para ler"""
    try:
        contents = repo_ref.get_contents(nome_arquivo)
        # Cria um arquivo temporário na memória
        arquivo_memoria = io.BytesIO(contents.decoded_content)
        return Document(arquivo_memoria), contents.sha
    except Exception as e:
        st.error(f"Erro ao ler {nome_arquivo}: {e}")
        return None, None

def salvar_no_github(nome_arquivo, documento_docx, sha_original, mensagem):
    """Envia o arquivo modificado de volta para o GitHub"""
    try:
        # Salva o documento modificado em memória
        arquivo_salvar = io.BytesIO()
        documento_docx.save(arquivo_salvar)
        novo_conteudo = arquivo_salvar.getvalue()
        
        # Envia para o GitHub (Atualiza o arquivo)
        repo_ref.update_file(
            path=nome_arquivo,
            message=mensagem,
            content=novo_conteudo,
            sha=sha_original
        )
        st.toast("✅ Salvo no GitHub com sucesso!", icon="☁️")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def ler_tabela_formatada(doc, tipo):
    lista = []
    if doc:
        for tabela in doc.tables:
            for linha in tabela.rows:
                if len(linha.cells) >= 2:
                    nome = linha.cells[1].text.strip()
                    obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                    if len(nome) > 3 and "NOME" not in nome.upper():
                        lista.append({"Nome": nome, "Situação": tipo, "Obs": obs})
    return lista

# --- INTERFACE DO SISTEMA ---
st.title("🏫 Sistema Escolar Online (Com Salvamento Automático)")

tab1, tab2 = st.tabs(["🔍 Pesquisar", "📝 Cadastrar Novo Aluno"])

# --- ABA 1: PESQUISAR ---
with tab1:
    # Carrega os arquivos do GitHub na hora
    doc_passivos, sha_p = carregar_dados_github(ARQ_PASSIVOS)
    doc_concluintes, sha_c = carregar_dados_github(ARQ_CONCLUINTES)
    
    lista_final = ler_tabela_formatada(doc_passivos, "Passivo") + ler_tabela_formatada(doc_concluintes, "Concluinte")
    df = pd.DataFrame(lista_final)

    busca = st.text_input("Buscar Aluno:", placeholder="Digite o nome...")
    if busca and not df.empty:
        res = df[df['Nome'].str.contains(busca, case=False, na=False)]
        st.dataframe(res, use_container_width=True)

# --- ABA 2: CADASTRAR (A MÁGICA) ---
with tab2:
    st.header("Cadastrar Novo Aluno")
    
    with st.form("form_cadastro"):
        novo_nome = st.text_input("Nome Completo")
        nova_obs = st.text_input("Observação")
        arquivo_destino = st.radio("Onde salvar?", ["EMEF PA-RESSACA (Passivos)", "CONCLUINTES"])
        
        enviar = st.form_submit_button("💾 SALVAR NO SISTEMA")
        
        if enviar and novo_nome:
            with st.spinner("Salvando na nuvem..."):
                # Define qual arquivo abrir
                if "CONCLUINTES" in arquivo_destino:
                    nome_arq = ARQ_CONCLUINTES
                    doc_atual, sha_atual = doc_concluintes, sha_c
                else:
                    nome_arq = ARQ_PASSIVOS
                    doc_atual, sha_atual = doc_passivos, sha_p
                
                # Adiciona na primeira tabela que achar (ou na última)
                if len(doc_atual.tables) > 0:
                    tabela = doc_atual.tables[0] # Pega a primeira tabela
                    nova_linha = tabela.add_row()
                    nova_linha.cells[0].text = "NOVO" # Numero
                    nova_linha.cells[1].text = novo_nome # Nome
                    if len(nova_linha.cells) > 2:
                        nova_linha.cells[2].text = nova_obs # Obs
                    
                    # Salva de volta no GitHub
                    sucesso = salvar_no_github(nome_arq, doc_atual, sha_atual, f"Adicionado aluno: {novo_nome}")
                    
                    if sucesso:
                        st.success(f"Aluno {novo_nome} cadastrado com sucesso! Pode pesquisar.")
                        st.rerun() # Atualiza a página
                else:
                    st.error("O arquivo Word não tem tabelas para adicionar.")
