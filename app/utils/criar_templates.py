import streamlit as st
import pandas as pd
import mysql.connector
import os
import base64
from datetime import datetime
from utils.db import salvar_template_db, listar_templates_db, excluir_template, conectar
# ---------------------------------
# Insere Templates
# ---------------------------------
# --------------------------------
# FUNÇÕES DE APOIO (LAYOUT)
# --------------------------------

def criar_link_download_clean(caminho_arquivo, nome_exibicao):
    """Gera link de download via Base64 (Preservado conforme original)"""
    if not caminho_arquivo:
        return "<span style='color: gray;'>Não disponível</span>"
    
   # Pega apenas o nome do arquivo para garantir que não haja caminhos duplicados
    nome_fisico = os.path.basename(caminho_arquivo)    
    # Localização correta: Raiz do Projeto -> assets -> templates
    caminho_completo = os.path.join(os.getcwd(), "assets", "templates", nome_fisico)
    
    if os.path.exists(caminho_completo):
        try:
            with open(caminho_completo, "rb") as f:
                data = f.read()
                
            b64 = base64.b64encode(data).decode()
            
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if nome_fisico.endswith('.xlsx') else "application/octet-stream"
            href = f'<a href="data:{mime_type};base64,{b64}" download="{nome_exibicao}" style="text-decoration: none; color: #1f77b4; font-weight: bold;">📄 {nome_exibicao}</a>'
            return href
        except Exception as e:
            return f"<span style='color: red;'>Erro de leitura</span>"
    
    return "<span style='color: gray;'>Indisponível (Offline)</span>"

# --------------------------------
# PÁGINA DO TEMPLATE 
# --------------------------------

def cria_templates_page():
    st.header("📂 Gerenciador de Templates")
    
    # 1. INICIALIZAÇÃO DE ESTADOS
    if "ger_in_desc_val" not in st.session_state: st.session_state.ger_in_desc_val = ""
    if "ger_sel_trim_index" not in st.session_state: st.session_state.ger_sel_trim_index = 0
    if "ger_id_editando" not in st.session_state: st.session_state.ger_id_editando = None
    if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0

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
        
        arquivo = st.file_uploader("Enviar Template", key=f"file_uploader_{st.session_state.uploader_key}")
        
        texto_botao = "💾 Atualizar Template" if st.session_state.ger_id_editando else "💾 Salvar Template"
        
        if st.button(texto_botao, type="primary", use_container_width=False):
            if nome_form:
                # Chama a lógica que está no db.py enviando os dados do layout
                sucesso = salvar_template_db(nome_form, template, arquivo, st.session_state.ger_id_editando)
                
                if sucesso:
                    # Limpeza de estados após sucesso
                    st.session_state.ger_in_desc_val = ""
                    st.session_state.ger_sel_trim_index = 0
                    st.session_state.ger_id_editando = None
                    st.session_state.uploader_key += 1 
                    
                    st.success("✅ Operação realizada com sucesso!")
                    st.rerun()
            else:
                st.warning("⚠️ Preencha a descrição do template.")

    st.write("") 

    # --- SEÇÃO 2: LISTAGEM (TABELA COM AÇÕES - LAYOUT PRESERVADO) ---
    st.subheader("📋 Templates Ativos no Sistema")
    
    # Busca os dados através da função do db.py
    df_arq = listar_templates_db()
    
    if not df_arq.empty:
        with st.container(border=True):
            # Larguras originais preservadas
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
                
                link_html = criar_link_download_clean(row['caminho_arquivo'], row['nome_arquivo_original'])
                c[3].markdown(link_html, unsafe_allow_html=True)
                
                with c[4]:
                    btn_col1, btn_col2 = st.columns(2)
                    
                    # Ação de Editar
                    if btn_col1.button("✏️", key=f"edit_{row['id']}", help="Editar template"):
                        st.session_state.ger_in_desc_val = row['nome_formulario']
                        st.session_state.ger_id_editando = row['id']
                        if row['template'] in trimestres_opcoes:
                            st.session_state.ger_sel_trim_index = trimestres_opcoes.index(row['template'])
                        st.rerun()

                    # Ação de Excluir
                    if btn_col2.button("🗑️", key=f"del_{row['id']}", help="Excluir template"):
                        # Usa a função de delete que já existe no seu db.py
                        if excluir_template(row['id']):
                            st.toast("Template removido!")
                            st.rerun()
                
                st.markdown('<hr style="margin: 0.3rem 0; opacity: 0.1;">', unsafe_allow_html=True)
    else:
        st.info("Nenhum template encontrado.")