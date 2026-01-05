import streamlit as st
import pandas as pd
import os
from docx import Document

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Secretaria Escolar", page_icon="🎓", layout="wide")

# --- CSS VISUAL (AZUL PROFISSIONAL) ---
st.markdown("""
    <style>
    /* Esconde menu do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Cabeçalho Azul */
    .header-azul {
        background: linear-gradient(90deg, #00A8C6 0%, #007EA7 100%);
        padding: 20px;
        border-radius: 8px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Cartões de Alunos */
    .card-aluno {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 6px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .card-aluno:hover {
        transform: scale(1.01);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- NOMES EXATOS DOS SEUS ARQUIVOS ---
ARQ_PASSIVOS = 'EMEF PA-RESSACA.docx'
ARQ_CONCLUINTES = 'CONCLUINTES- PA-RESSACA.docx'

def ler_tabelas_word(arquivo, tipo_situacao):
    """Lê as tabelas do Word ignorando cabeçalhos e linhas vazias"""
    lista = []
    
    if not os.path.exists(arquivo):
        return []

    try:
        doc = Document(arquivo)
        for tabela in doc.tables:
            for linha in tabela.rows:
                # Verifica se a linha tem células suficientes
                # Coluna 0 = Número, Coluna 1 = Nome
                if len(linha.cells) >= 2:
                    nome = linha.cells[1].text.strip()
                    obs = linha.cells[2].text.strip() if len(linha.cells) > 2 else ""
                    
                    # Filtros de limpeza (Ignora cabeçalhos e vazios)
                    if not nome: continue
                    if "NOME" in nome.upper(): continue
                    if "NUMERO" in nome.upper(): continue
                    
                    lista.append({
                        "Nome": nome,
                        "Situação": tipo_situacao,
                        "Observação": obs,
                        "Arquivo": arquivo
                    })
    except Exception as e:
        st.error(f"Erro ao ler {arquivo}: {e}")
        
    return lista

def carregar_tudo():
    """Junta os dados dos dois arquivos"""
    dados_p = ler_tabelas_word(ARQ_PASSIVOS, "Passivo")
    dados_c = ler_tabelas_word(ARQ_CONCLUINTES, "Concluinte")
    return pd.DataFrame(dados_p + dados_c)

# --- TELA PRINCIPAL ---

st.markdown('<div class="header-azul"><h1>🎓 CADASTRO E BUSCA DE ALUNOS</h1></div>', unsafe_allow_html=True)

# Verifica arquivos
if not os.path.exists(ARQ_PASSIVOS) or not os.path.exists(ARQ_CONCLUINTES):
    st.error("⚠️ FALTAM ARQUIVOS NA PASTA!")
    st.info(f"Coloque '{ARQ_PASSIVOS}' e '{ARQ_CONCLUINTES}' junto com este arquivo.")
else:
    # --- ÁREA DE BUSCA ---
    termo = st.text_input("🔍 Digite o nome para buscar:", placeholder="Ex: Ana Clara...")

    if termo:
        df = carregar_tudo()
        
        if not df.empty:
            # Filtra pelo nome
            resultado = df[df['Nome'].str.contains(termo, case=False, na=False)]
            
            if not resultado.empty:
                st.success(f"Encontrado(s): {len(resultado)}")
                
                for i, row in resultado.iterrows():
                    # Define cor da borda (Azul = Concluinte, Vermelho = Passivo)
                    cor = "#00A8C6" if row['Situação'] == "Concluinte" else "#FF6B6B"
                    
                    st.markdown(f"""
                    <div class="card-aluno" style="border-left-color: {cor};">
                        <h3 style="margin:0; color: #333;">{row['Nome']}</h3>
                        <p style="margin:5px 0 0 0; color: #555;">
                            <strong>Situação:</strong> {row['Situação']} <br>
                            <strong>Obs:</strong> {row['Observação']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("Nenhum aluno encontrado.")
        else:
            st.info("Nenhum dado encontrado nos arquivos.")
    else:
        st.caption("Digite um nome acima para pesquisar em todos os documentos.")