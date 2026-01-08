import streamlit as st
import os
import time
import pandas as pd
from datetime import datetime
# Importando as funções centralizadas do db.py
from utils.db import registrar_no_banco, consultar_base_ativa, deletar_material_db
from utils.agente_ia_mysql import processar_conteudo_ia 

# Configuração de caminhos
KNOWLEDGE_DIR = "knowledge_base"
if not os.path.exists(KNOWLEDGE_DIR):
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

def limpar_formulario():
    # Esta função agora é chamada apenas via callback ou após st.rerun
    st.session_state.form_descricao = ""
    st.session_state.form_url_yt = ""    
    st.session_state.uploader_id += 1

def ia_manager_page():
    usuario_id = st.session_state.get("usuario_id", 1)
    
    st.markdown("""
        <style>
            div.stButton > button[kind="primary"] {
                background-color: #00acee !important;
                color: white !important;
                border-radius: 8px;
                width: 100%;
            }
            .stExpander { border: 1px solid #e6e9ef; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🧠 Base de Conhecimento IA")
    st.info("Gerencie os documentos e vídeos que servem de base para a inteligência da plataforma.")
    
    # Inicialização segura do estado
    if "form_descricao" not in st.session_state: st.session_state.form_descricao = ""
    if "form_url_yt" not in st.session_state: st.session_state.form_url_yt = ""
    if "uploader_id" not in st.session_state: st.session_state.uploader_id = 0
        
    with st.expander("➕ Adicionar Novo Material", expanded=True):
        tipo = st.radio("Tipo de Conteúdo:", ["Arquivo (PDF)", "Link do YouTube"], horizontal=True)
        
        # Widget de texto
        st.text_input("Descrição curta do material", placeholder="Ex: Manual de Metas Q3", key="form_descricao")
        
        if tipo == "Arquivo (PDF)":
            upload = st.file_uploader("Selecione o PDF", type=["pdf"], key=f"file_up_{st.session_state.uploader_id}")
            col1, col2, _ = st.columns([1, 1, 2])
            with col1:
                btn_salvar = st.button("🚀 Processar e Salvar", type="primary", key="btn_save_pdf")
            with col2:
                # Limpeza via botão direto
                st.button("🧹 Limpar", key="btn_limpar_pdf", on_click=limpar_formulario)

            if btn_salvar:
                if not upload:
                    st.warning("⚠️ Por favor, selecione um arquivo PDF.")
                elif not st.session_state.form_descricao:
                    st.warning("⚠️ Adicione uma descrição para organizar a base.")
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{timestamp}_{upload.name.replace(' ', '_')}"
                    final_path = os.path.join(KNOWLEDGE_DIR, filename)
                    
                    try:
                        with open(final_path, "wb") as f:
                            f.write(upload.getbuffer())
                        
                        with st.spinner("🤖 A IA está lendo e indexando o documento..."):
                            sucesso, resultado, _ = processar_conteudo_ia(final_path, nome_para_db=upload.name)
                            
                            if sucesso:
                                # Salvando no banco (TiDB/MySQL)
                                if registrar_no_banco(upload.name, 'arquivo', final_path, st.session_state.form_descricao, resultado):
                                    st.success("✅ Documento indexado com sucesso!")
                                    time.sleep(1)
                                    # CORREÇÃO: Limpamos o estado ANTES do rerun para evitar o erro de 'instantiated'
                                    st.session_state.form_descricao = ""
                                    st.session_state.uploader_id += 1
                                    st.rerun()
                            else:
                                st.error(f"❌ Falha na IA: {resultado}")
                                if os.path.exists(final_path): os.remove(final_path)
                    except Exception as e:
                        # Se o erro de session_state persistisse, ele apareceria aqui
                        st.error(f"❌ Erro ao processar: {e}")

        else: # YouTube
            st.text_input("Cole a URL do Vídeo (Youtube)", placeholder="https://www.youtube.com/watch?v=...", key="form_url_yt")
            col1, col2, _ = st.columns([1, 1, 2])
            with col1:
                btn_yt = st.button("🚀 Processar e Salvar", type="primary", key="btn_save_yt")
            with col2:
                st.button("🧹 Limpar", key="btn_limpar_yt", on_click=limpar_formulario)

            if btn_yt:
                url = st.session_state.form_url_yt
                if "youtube.com" in url or "youtu.be" in url:
                    with st.spinner("🤖 Analisando vídeo e gerando base de conhecimento..."):
                        sucesso, resultado, _ = processar_conteudo_ia(url)
                        if sucesso:
                            if registrar_no_banco("Vídeo YouTube", 'youtube', url, st.session_state.form_descricao, resultado):
                                st.success("✅ Conhecimento do vídeo extraído!")
                                time.sleep(1)
                                st.session_state.form_descricao = ""
                                st.session_state.form_url_yt = ""
                                st.rerun()
                        else:
                            st.error(f"❌ Erro no vídeo: {resultado}")
                else:
                    st.warning("⚠️ Insira uma URL válida do YouTube.")

    st.divider()
    exibir_listagem()

def exibir_listagem():
    st.subheader("📚 Base Ativa")
    df = consultar_base_ativa()
    
    if not df.empty:
        cols_h = st.columns([0.5, 0.5, 0.3, 0.3])                
        cols_h[0].markdown("**Descrição**") 
        cols_h[1].markdown("**Material**")
        cols_h[2].markdown("**Data**")
        cols_h[3].markdown("**Ação**")
        
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([0.5, 0.5, 0.3, 0.3])
            c1.write(row['descricao'] or "---")
            icone = "📄" if row['tipo_conteudo'] == 'arquivo' else "🎥"
            c2.write(f"{icone} {row['nome']}")
            
            dt = row['data_subida']
            c3.write(dt.strftime("%d/%m/%Y") if hasattr(dt, 'strftime') else str(dt))
            
            with c4:                
                if st.button("🗑️", key=f"admin_tab_conhecimento_del_{row['id']}"):
                    remover_material_logica(row['id'], row['caminho_ou_url'], row['tipo_conteudo'])
            st.markdown('<hr style="margin: 0.2rem 0; opacity: 0.1;">', unsafe_allow_html=True)
    else:
        st.info("A base de conhecimento está vazia.")

def remover_material_logica(id_db, caminho, tipo):
    if deletar_material_db(id_db):
        if tipo == 'arquivo' and caminho and os.path.exists(caminho):
            try: os.remove(caminho)
            except: pass
        
        st.toast("Material removido da base!")  
        time.sleep(0.5)             
        st.rerun()