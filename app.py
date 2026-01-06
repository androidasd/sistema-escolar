import streamlit as st
import pandas as pd
from docx import Document
from github import Github
import io

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Secretaria Escolar", page_icon="🏫", layout="wide")

# --- CONEXÃO COM GITHUB ---
try:
    # Pega a chave que você salvou no site do Streamlit
    TOKEN = st.secrets["GITHUB_TOKEN"]
    g = Github(TOKEN)
    
    # Tenta achar o seu repositório automaticamente
    user = g.get_user()
    repo_ref = None
    # Procura o repositório chamado 'sistema-escolar'
    for repo in user.get_repos():
        if "sistema-escolar" in repo.name:
            repo_ref = repo
            break
            
    if not repo_ref:
        st.error("Erro: Não encontrei o repositório 'sistema-escolar' no seu GitHub.")
        st.stop()

except Exception as e:
    st.error(f"Erro de Conexão: Verifique se configurou o Secrets corretamente. Detalhe: {e}")
    st.stop()

# Nomes exatos dos seus arquivos
ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

# --- FUNÇÕES ---

def carregar_do_github(nome_arquivo):
    """Baixa o arquivo Word do GitHub para a memória"""
    try:
        contents = repo_ref.get_contents(nome_arquivo)
        return Document(io.BytesIO(contents.decoded_content)), contents.sha
    except:
        return None, None

def salvar_no_github(nome_arquivo, doc, sha_original, aluno_nome):
    """Salva o arquivo alterado de volta no GitHub"""
    try:
        # Salva o Word na memória
        buffer = io.BytesIO()
        doc.save(buffer)
        novo_conteudo = buffer.getvalue()
        
        # Envia para o GitHub
        repo_ref.update_file(
            path=nome_arquivo,
            message=f"Novo aluno cadastrado: {aluno_nome}",
            content=novo_conteudo,
            sha=sha_original
        )
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def ler_tabela(doc, tipo):
    """Lê os dados para mostrar na pesquisa"""
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

# --- TELA DO SISTEMA ---

st.title("🏫 Sistema Escolar Online")

# Cria as duas abas
tab1, tab2 = st.tabs(["🔍 PESQUISAR ALUNO", "📝 CADASTRAR NOVO"])

# --- ABA 1: PESQUISA ---
with tab1:
    st.write("Digite o nome abaixo para buscar nos arquivos:")
    busca = st.text_input("Nome do Aluno:", placeholder="Ex: Ana...")
    
    if busca:
        with st.spinner("Buscando no arquivo..."):
            doc_p, _ = carregar_do_github(ARQ_PASSIVOS)
            doc_c, _ = carregar_do_github(ARQ_CONCLUINTES)
            
            dados = ler_tabela(doc_p, "Passivo") + ler_tabela(doc_c, "Concluinte")
            df = pd.DataFrame(dados)
            
            if not df.empty:
                res = df[df['Nome'].str.contains(busca, case=False, na=False)]
                if not res.empty:
                    st.success(f"{len(res)} alunos encontrados!")
                    st.dataframe(res, use_container_width=True)
                else:
                    st.warning("Nenhum aluno encontrado.")

# --- ABA 2: CADASTRO (SALVA AUTOMÁTICO) ---
with tab2:
    st.markdown("### Cadastrar Novo Aluno")
    st.info("ℹ️ Ao clicar em salvar, o sistema edita o Word e atualiza seu GitHub automaticamente.")
    
    with st.form("cadastro"):
        nome_novo = st.text_input("Nome Completo:")
        obs_nova = st.text_input("Observação:")
        destino = st.radio("Onde salvar?", ["EMEF PA-RESSACA (Passivos)", "CONCLUINTES"])
        
        btn_salvar = st.form_submit_button("💾 SALVAR CADASTRO")
        
        if btn_salvar and nome_novo:
            with st.spinner("Conectando ao GitHub e salvando..."):
                # Escolhe o arquivo certo
                arquivo_alvo = ARQ_CONCLUINTES if "CONCLUINTES" in destino else ARQ_PASSIVOS
                doc_atual, sha_atual = carregar_do_github(arquivo_alvo)
                
                if doc_atual:
                    # Adiciona na primeira tabela
                    if len(doc_atual.tables) > 0:
                        tabela = doc_atual.tables[0]
                        nova_linha = tabela.add_row()
                        nova_linha.cells[0].text = "NOVO"
                        nova_linha.cells[1].text = nome_novo
                        if len(nova_linha.cells) > 2:
                            nova_linha.cells[2].text = obs_nova
                        
                        # Salva
                        if salvar_no_github(arquivo_alvo, doc_atual, sha_atual, nome_novo):
                            st.toast("✅ Salvo com sucesso!", icon="🎉")
                            st.success(f"Aluno '{nome_novo}' salvo no arquivo {arquivo_alvo}!")
                            st.balloons()
                    else:
                        st.error("O arquivo Word não tem tabela para escrever.")
                else:
                    st.error("Erro ao carregar arquivo do GitHub.")
