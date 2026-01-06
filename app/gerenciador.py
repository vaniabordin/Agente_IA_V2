import streamlit as st
import pandas as pd
import mysql.connector
import os
import base64
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configurações de Pastas e Limites
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE_MB = 10

# --------------------------------
# FUNÇÕES DE APOIO
# --------------------------------

def get_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME")
        )
    except mysql.connector.Error as e:
        st.error(f"Erro ao conectar no banco: {e}")
        return None

def criar_link_download_clean(caminho_arquivo, nome_exibicao):
    if caminho_arquivo and os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{nome_exibicao}" style="text-decoration: none; color: #1f77b4; font-weight: bold;">📄 {nome_exibicao}</a>'
        return href
    return "<span style='color: gray;'>Não disponível</span>"

def excluir_arquivo_logica(id_arquivo):
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT caminho_arquivo FROM arquivos_templates WHERE id = %s", (id_arquivo,))
        caminho = cursor.fetchone()
        if caminho and os.path.exists(caminho[0]):
            try: os.remove(caminho[0])
            except: pass
        cursor.execute("DELETE FROM arquivos_templates WHERE id = %s", (id_arquivo,))
        conn.commit()
        conn.close()
        st.rerun()

# --------------------------------
# PÁGINA DO GERENCIADOR
# --------------------------------

def gerenciador_page():
    st.header("📂 Gerenciador de Templates")
    
    # 1. INICIALIZAÇÃO DE ESTADOS
    if "ger_in_desc_val" not in st.session_state:
        st.session_state.ger_in_desc_val = ""
    if "ger_sel_trim_index" not in st.session_state:
        st.session_state.ger_sel_trim_index = 0
    if "ger_id_editando" not in st.session_state:
        st.session_state.ger_id_editando = None
    # Contador para resetar o componente de upload
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    trimestres_opcoes = ["Q1", "Q2", "Q3", "Q4"]

    # --- SEÇÃO 1: FORMULÁRIO (CADASTRO / EDIÇÃO) ---
    with st.container(border=True):
        status_titulo = "✏️ Editando Template" if st.session_state.ger_id_editando else "➕ Novo Template"
        st.subheader(status_titulo)
        
        col1, col2 = st.columns(2)
        with col1:
            template = st.selectbox(
                "Trimestre", 
                trimestres_opcoes, 
                index=st.session_state.ger_sel_trim_index,
                key="widget_trimestre_select"
            )
        with col2:
            nome_form = st.text_input(
                "Descrição (Ex: 1.0 Diagnóstico)", 
                value=st.session_state.ger_in_desc_val,
                key="widget_descricao_input" 
            )
        
        # O widget usa uma key dinâmica que muda após o salvamento para limpar o arquivo selecionado
        arquivo = st.file_uploader("Enviar Template", key=f"file_uploader_{st.session_state.uploader_key}")
        
        texto_botao = "💾 Atualizar Template" if st.session_state.ger_id_editando else "💾 Salvar Template"
        
        if st.button(texto_botao, type="primary", use_container_width=False):
            if nome_form:
                conn = get_connection()
                if conn:
                    cursor = conn.cursor()
                    try:
                        caminho = None
                        if arquivo:
                            caminho = os.path.join(UPLOAD_DIR, f"{datetime.now().strftime('%Y%m%d%H%M')}_{arquivo.name}")
                            with open(caminho, "wb") as f: 
                                f.write(arquivo.read())

                        if st.session_state.ger_id_editando:
                            if arquivo:
                                sql = """UPDATE arquivos_templates 
                                        SET nome_formulario=%s, template=%s, nome_arquivo_original=%s, 
                                            caminho_arquivo=%s, tipo_arquivo=%s, data_upload=NOW()
                                        WHERE id=%s"""
                                cursor.execute(sql, (nome_form, template, arquivo.name, caminho, arquivo.type, st.session_state.ger_id_editando))
                            else:
                                sql = "UPDATE arquivos_templates SET nome_formulario=%s, template=%s WHERE id=%s"
                                cursor.execute(sql, (nome_form, template, st.session_state.ger_id_editando))
                        else:
                            if arquivo:
                                sql = """INSERT INTO arquivos_templates 
                                        (nome_formulario, template, nome_arquivo_original, caminho_arquivo, tipo_arquivo, status, data_upload) 
                                        VALUES (%s, %s, %s, %s, %s, %s, NOW())"""
                                cursor.execute(sql, (nome_form, template, arquivo.name, caminho, arquivo.type, "ativo"))
                            else:
                                st.error("❌ O arquivo é obrigatório para novos cadastros.")
                                st.stop()

                        conn.commit()
                        
                        # --- LIMPEZA E RESET APÓS SUCESSO ---
                        st.session_state.ger_in_desc_val = ""
                        st.session_state.ger_sel_trim_index = 0
                        st.session_state.ger_id_editando = None
                        st.session_state.uploader_key += 1 # Incrementa para resetar o file_uploader
                        
                        st.success("✅ Operação realizada com sucesso!")
                        st.rerun()
                                            
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")
                    finally:
                        conn.close()
            else:
                st.warning("⚠️ Preencha a descrição do template.")

    st.write("") 

    # --- SEÇÃO 2: LISTAGEM (TABELA COM AÇÕES) ---
    st.subheader("📋 Templates Ativos no Sistema")
    conn = get_connection()
    if conn:
        try:
            df_arq = pd.read_sql("SELECT id, nome_formulario, template, nome_arquivo_original, caminho_arquivo, status FROM arquivos_templates ORDER BY template ASC, id DESC", conn)
            
            if not df_arq.empty:
                with st.container(border=True):
                    larguras = [0.5, 2.5, 0.8, 3, 1.2]
                    h_col = st.columns(larguras)
                    h_col[0].write("**ID**")
                    h_col[1].write("**Descrição**")
                    h_col[2].write("**Trimestre**")
                    h_col[3].write("**Arquivo**")
                    h_col[4].write("**Ações**")
                    st.divider()
                    
                    for _, row in df_arq.iterrows():
                        c = st.columns(larguras)
                        c[0].write(f"`{row['id']}`")
                        c[1].write(row['nome_formulario'])
                        c[2].write(row['template'])
                        c[3].markdown(criar_link_download_clean(row['caminho_arquivo'], row['nome_arquivo_original']), unsafe_allow_html=True)
                  
                        with c[4]:
                            btn_col1, btn_col2 = st.columns(2)
                            
                            if btn_col1.button("✏️", key=f"edit_{row['id']}", help="Editar template"):
                                st.session_state.ger_in_desc_val = row['nome_formulario']
                                st.session_state.ger_id_editando = row['id']
                                if row['template'] in trimestres_opcoes:
                                    st.session_state.ger_sel_trim_index = trimestres_opcoes.index(row['template'])
                                st.rerun()

                            if btn_col2.button("🗑️", key=f"del_{row['id']}", help="Excluir template"):
                                excluir_arquivo_logica(row['id'])
                        
                        st.markdown('<hr style="margin: 0.3rem 0; opacity: 0.1;">', unsafe_allow_html=True)
            else:
                st.info("Nenhum template encontrado.")
        finally:
            conn.close()