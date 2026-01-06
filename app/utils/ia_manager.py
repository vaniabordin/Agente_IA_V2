import streamlit as st
import os
import base64
import time
import pandas as pd
from datetime import datetime
from utils.db import conectar
from utils.agente_ia_mysql import processar_conteudo_ia

# Configuração de caminhos
KNOWLEDGE_DIR = "knowledge_base"
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# --- FUNÇÃO DE LIMPEZA (CALLBACK) ---
def limpar_formulario():
    """Reseta as descrições e incrementa a versão do uploader para limpá-lo"""
    st.session_state.form_descricao = ""
    st.session_state.form_url_yt = ""
    # Incrementa um contador para resetar o widget de arquivo
    st.session_state.uploader_id += 1

def ia_manager_page():
    # --- AJUSTE DE CSS ---
    st.markdown("""
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #00acee !important;
            color: white !important;
            border-radius: 8px;
            width: 100%;
        }
        div.stButton > button[key*="btn_limpar"] {
            background-color: #28a745 !important;
            color: white !important;
            border-radius: 8px;
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🧠 Base de Conhecimento IA")
    
    # Inicialização do State
    if "form_descricao" not in st.session_state:
        st.session_state.form_descricao = ""
    if "form_url_yt" not in st.session_state:
        st.session_state.form_url_yt = ""
    if "uploader_id" not in st.session_state:
        st.session_state.uploader_id = 0
        
    with st.expander("➕ Adicionar Novo Material", expanded=True):
        tipo = st.radio("Tipo de Conteúdo:", ["Arquivo (PDF)", "Link do YouTube"], horizontal=True)
        st.text_input("Descrição do material", placeholder="Ex: Manual de Metas Q3", key="form_descricao")
        
        if tipo == "Arquivo (PDF)":
            # A key muda toda vez que clicamos em limpar, resetando o arquivo selecionado
            upload = st.file_uploader("Subir arquivo", type=["pdf"], key=f"file_up_{st.session_state.uploader_id}")
            
            col1, col2, _ = st.columns([1, 1, 2])
            with col1:
                btn_salvar = st.button("Salvar", type="primary", key="btn_save_pdf")
            with col2:
                st.button("Limpar", key="btn_limpar_pdf", on_click=limpar_formulario)

            if btn_salvar:
                if not upload:
                    st.warning("Selecione um arquivo.")
                else:
                    timestamp = datetime.now().strftime("%Y%m%d%H%M")
                    filename = f"{timestamp}_{upload.name}"
                    final_path = os.path.join(KNOWLEDGE_DIR, filename)
                    with open(final_path, "wb") as f:
                        f.write(upload.getbuffer()) 
                    
                    with st.spinner("Processando Arquivo..."):
                        sucesso, resultado = processar_conteudo_ia(final_path, nome_para_db=f"REF/{upload.name}")
                        if sucesso:                             
                            registrar_no_banco(upload.name, 'arquivo', final_path, st.session_state.form_descricao, resultado)
                            st.success("✅ Material inserido com sucesso!", icon="🎉") # Notificação flutuante
                            time.sleep(2) #
                            st.rerun()
                        else:
                            st.error(f"❌ Erro: {resultado}")

        else: # YouTube
            st.text_input("URL do YouTube", key="form_url_yt")
            col1, col2, _ = st.columns([1, 1, 2])
            with col1:
                btn_yt = st.button("Salvar", type="primary", key="btn_save_yt")
            with col2:
                st.button("Limpar", key="btn_limpar_yt", on_click=limpar_formulario)

            if btn_yt:
                if st.session_state.form_url_yt:
                    with st.spinner("Processando Vídeo..."):                        
                        sucesso, resultado = processar_conteudo_ia(st.session_state.form_url_yt, nome_para_db=f"REF/YT_VIDEO")
                        if sucesso:
                            registrar_no_banco("Vídeo YouTube", 'youtube', st.session_state.form_url_yt, st.session_state.form_descricao, resultado)
                            st.success("✅ Vídeo inserido com sucesso!", icon="🎉")
                            time.sleep(2)
                            st.rerun()
                else:
                    st.warning("Insira a URL.")

    st.divider()
    exibir_listagem()

# --- FUNÇÃO DE REGISTRO NO BANCO ---
def registrar_no_banco(nome, tipo, caminho, descricao, texto_extraido=""):
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            sql = "INSERT INTO ia_conhecimento (nome, tipo_conteudo, caminho_ou_url, conteudo, descricao, status) VALUES (%s, %s, %s, %s, %s, 'ativo')"
            cursor.execute(sql, (nome, tipo, caminho, texto_extraido, descricao))
            conn.commit()
        finally:
            conn.close()

# --- FUNÇÃO DE LISTAGEM ---
def exibir_listagem():
    st.subheader("📚 Materiais Cadastrados")
    conn = conectar()
    if conn:
        try:
            query = "SELECT id, nome, tipo_conteudo, caminho_ou_url, descricao, data_subida FROM ia_conhecimento ORDER BY id DESC"
            df = pd.read_sql(query, conn)
            if not df.empty:
                h1, h2, h3, h4 = st.columns([0.3, 0.3, 0.3, 0.3])
                h1.markdown("**Descrição**"); h2.markdown("**Material**"); h3.markdown("**Data**"); h4.markdown("**Ação**")
                st.divider()
                for index, row in df.iterrows():
                    c1, c2, c3, c4 = st.columns([0.5, 0.5, 0.2, 0.2])
                    c1.write(row['descricao'] if row['descricao'] else "---")
                    icone = "📄" if row['tipo_conteudo'] == 'arquivo' else "🎥"
                    c2.write(f"{icone} {row['nome']}")                    
                    dt = row['data_subida']
                    c3.write(dt.strftime("%d/%m/%Y") if hasattr(dt, 'strftime') else str(dt))
                    with c4:
                        if st.button("🗑️", key=f"del_{row['id']}_{index}"):
                            remover_material(row['id'], row['caminho_ou_url'], row['tipo_conteudo'])
                    st.markdown('<hr style="margin: 0.5rem 0; opacity: 0.1;">', unsafe_allow_html=True)
            else:
                st.info("Nenhum material encontrado.")
        finally:
            conn.close()

# --- FUNÇÃO DE REMOÇÃO ---
def remover_material(id_db, caminho, tipo):
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ia_conhecimento WHERE id = %s", (id_db,))
            if tipo == 'arquivo' and caminho and os.path.exists(caminho):
                try: os.remove(caminho)
                except: pass
            conn.commit()
            st.rerun()
        finally:
            conn.close()