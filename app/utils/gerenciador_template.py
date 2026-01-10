import streamlit as st
import pandas as pd
import mysql.connector
import os
from datetime import datetime


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------------
# CONEXÃO COM MYSQL (Usando Secrets)
# --------------------------------
def get_connection():
    try:
        # Puxando diretamente do bloco [mysql] do secrets.toml
        return mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=int(st.secrets["mysql"]["port"]),
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            ssl_verify_cert=True # Crucial para TiDB Cloud
        )
    except Exception as e:
        st.error(f"Erro de conexão com o Banco: {e}")
        return None

# --------------------------------
# PÁGINA PRINCIPAL
# --------------------------------
def gerenciador_page():
    st.title("📂 Gerenciador de Arquivos – Gemini")
    st.success("Acesso autorizado como ADMIN")

    # --------------------------------
    # FORMULÁRIO DE CADASTRO
    # --------------------------------
    st.subheader("➕ Novo arquivo")

    col1, col2 = st.columns(2)
    with col1:
        template = st.selectbox("Template", ["Q1", "Q2", "Q3", "Q4"])
    with col2:
        nome_formulario = st.text_input("Nome do formulário", placeholder="Ex: 01 persona")

    arquivo = st.file_uploader("Selecione o arquivo", type=None)

    if st.button("💾 Salvar arquivo", width="stretch"):
        if not nome_formulario or not arquivo:
            st.error("⚠️ Preencha todos os campos e selecione um arquivo.")
            return

        try:
            # Gerar nome único para evitar sobrescrever arquivos com mesmo nome
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            nome_salvo = f"{timestamp}_{arquivo.name}"
            caminho_arquivo = os.path.join(UPLOAD_DIR, nome_salvo)

            # Salvar arquivo fisicamente
            with open(caminho_arquivo, "wb") as f:
                f.write(arquivo.getbuffer()) # .getbuffer() é mais eficiente para Streamlit

            # Salvar no Banco
            conn = get_connection()
            if conn:
                cursor = conn.cursor()
                sql = """
                    INSERT INTO arquivos_templates 
                    (nome_formulario, template, nome_arquivo_original, caminho_arquivo, tipo_arquivo, status, data_upload)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                cursor.execute(sql, (
                    nome_formulario, template, arquivo.name, 
                    caminho_arquivo, arquivo.type, "ativo"
                ))
                conn.commit()
                cursor.close()
                conn.close()
                
                st.success(f"✅ Arquivo '{arquivo.name}' salvo com sucesso!")
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")

    # --------------------------------
    # LISTAGEM DE ARQUIVOS
    # --------------------------------
    st.divider()
    st.subheader("📊 Arquivos cadastrados")

    conn = get_connection()
    if conn:
        try:
            query = "SELECT id, nome_formulario, template, nome_arquivo_original, status, data_upload FROM arquivos_templates ORDER BY data_upload DESC"
            df = pd.read_sql(query, conn)
            
            if df.empty:
                st.info("Nenhum arquivo cadastrado.")
            else:
                # Cabeçalho da tabela customizada
                h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 1, 3, 2, 1])
                h_col1.write("**Formulário**")
                h_col2.write("**Ref**")
                h_col3.write("**Arquivo**")
                h_col4.write("**Status**")
                h_col5.write("**Ação**")

                for _, row in df.iterrows():
                    with st.container(border=True):
                        c1, c2, c3, c4, c5 = st.columns([3, 1, 3, 2, 1])
                        c1.write(row['nome_formulario'])
                        c2.write(row["template"])
                        c3.write(f"`{row['nome_arquivo_original']}`")
                        c4.write(row["status"])
                        
                        if c5.button("🗑", key=f"del_{row['id']}", help="Excluir arquivo"):
                            excluir_arquivo(row['id'])
        finally:
            conn.close()

def excluir_arquivo(id_arquivo):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT caminho_arquivo FROM arquivos_templates WHERE id = %s", (id_arquivo,))
            resultado = cursor.fetchone()
            
            # 1. Deletar do banco primeiro (se falhar aqui, não deleta o arquivo)
            cursor.execute("DELETE FROM arquivos_templates WHERE id = %s", (id_arquivo,))
            conn.commit()

            # 2. Deletar o arquivo físico depois
            if resultado and resultado[0] and os.path.exists(resultado[0]):
                try:
                    os.remove(resultado[0])
                except Exception as e:
                    st.warning(f"O registro foi removido, mas o arquivo físico não pôde ser apagado: {e}")

            st.toast("Arquivo removido!") 
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")
        finally:
            conn.close()
            
 