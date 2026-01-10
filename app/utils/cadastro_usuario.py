import streamlit as st
import pandas as pd
import time
import os
from dotenv import load_dotenv
from utils.db import conectar, cadastrar_usuario_db, remover_usuario_db

# ==========================================================
# 1. CONFIGURAÇÃO DE CREDENCIAIS (HÍBRIDO: LOCAL/CLOUD)
# ==========================================================
load_dotenv()

def exibir_usuarios_admin():
    # --- ESTILIZAÇÃO CSS PRESERVADA ---
    st.markdown("""
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #00acee !important;
            color: white !important;
            border-radius: 8px;
            width: 100%;
        }
        </style>
    """, unsafe_allow_html=True)

    st.subheader("➕ Cadastrar Novo Usuário")
    
    # --- FORMULÁRIO DE CADASTRO ---
    with st.container(border=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            novo_user = st.text_input("Username", placeholder="Ex: aluno_01", key="cad_username")
        with col2:
            nova_senha = st.text_input("Senha", type="password", key="cad_password")
        with col3:
            novo_role = st.selectbox("Perfil", ["aluno", "admin"], key="cad_role")
        
        c_btn, _, _ = st.columns([1, 1, 2])
        with c_btn:
            btn_salvar = st.button("Salvar Usuário", type="primary")
        
        if btn_salvar:
            if novo_user and nova_senha:
                sucesso, msg = cadastrar_usuario_db(novo_user, nova_senha, novo_role)
                if sucesso:
                    st.success(f"✅ {msg}")                   
                    time.sleep(1.2)
                    # O rerun limpa os campos automaticamente resetando os widgets pela 'key'
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ Preencha todos os campos.")

    st.divider()

    # --- LISTA DE USUÁRIOS (LAYOUT PRESERVADO) ---
    st.subheader("📋 Usuários Cadastrados")
    
    conn = conectar() # Usa sua função padrão de conexão para testar disponibilidade
    if conn:
        try:
            query = "SELECT id, username, role, ativo FROM usuarios ORDER BY username ASC"
            # O pandas usa o engine SQLAlchemy para converter SQL em DataFrame
            df_users = pd.read_sql(query, conn)
            
            if not df_users.empty:
                # Cabeçalho da Tabela
                h1, h2, h3, h4 = st.columns([0.3, 0.3, 0.2, 0.2])
                h1.markdown("**Usuário**")
                h2.markdown("**Perfil**")
                h3.markdown("**Status**")
                h4.markdown("**Ação**")
                st.divider()

                for _, row in df_users.iterrows():
                    c1, c2, c3, c4 = st.columns([0.3, 0.3, 0.2, 0.2])
                    c1.write(f"👤 {row['username']}")
                    c2.write(row['role'])
                    c3.write("✅ Ativo" if row['ativo'] else "❌ Inativo")
                    
                    with c4:
                        # Proteção para o usuário master não ser deletado por acidente
                        if row['username'].lower() == "master":
                            st.button("🔒", key=f"lock_{row['id']}", disabled=True, help="Usuário mestre")
                        else:
                            if st.button("🗑️", key=f"user_del_{row['id']}"):
                                if remover_usuario_db(row['id'], row['username']):
                                    st.toast(f"Usuário {row['username']} removido!")
                                    time.sleep(0.5)
                                    st.rerun()
                    
                    st.markdown('<hr style="margin: 0.5rem 0; opacity: 0.1;">', unsafe_allow_html=True)
            else:
                st.info("Nenhum usuário encontrado.")
        except Exception as e:
            st.error(f"Erro ao processar lista de usuários: {e}")
        finally:
            conn.close() # Importante para não travar o banco