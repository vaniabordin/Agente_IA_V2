import streamlit as st
import mysql.connector
import bcrypt
import os
from utils.ui import aplicar_estilo_fcj
from utils.db import cadastrar_usuario_db

# ---------------------------------------------------------
# 1. CONEXÃO COM O BANCO (Ajustada para TiDB Cloud + SSL)
# ---------------------------------------------------------
def get_connection():
    """Estabelece conexão com o banco usando drivers puros para evitar erros de SSL."""
    try:
        return mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=int(st.secrets["mysql"]["port"]),
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            use_pure=True,            # Essencial para evitar erro SSL 2026 no Windows
            ssl_disabled=False,       # Garante que a criptografia SSL exigida pelo TiDB esteja ativa
            connection_timeout=20
        )
    except Exception as e:
        st.error(f"❌ Erro ao conectar no banco: {e}")
        return None

# ---------------------------------------------------------
# 2. FUNÇÕES DE APOIO (Reset e Autenticação)
# ---------------------------------------------------------
def registrar_solicitacao_reset(identificador):
    """Registra uma solicitação de nova senha na tabela de suporte."""
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Garante que a tabela de recuperação exista
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recuperacao_senhas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    identificador VARCHAR(255),
                    data_solicitacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'Pendente'
                )
            """)
            cursor.execute("INSERT INTO recuperacao_senhas (identificador) VALUES (%s)", (identificador,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Erro ao registrar reset: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    return False

def authenticate(username, password):
    """Verifica credenciais no banco de dados com hash BCrypt."""
    conn = get_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, username, senha_hash, role, ativo FROM usuarios WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if user and user["ativo"]:
            hash_do_banco = user["senha_hash"]
            # Converte para bytes se necessário
            if isinstance(hash_do_banco, str):
                hash_do_banco = hash_do_banco.encode("utf-8")

            # Valida a senha digitada contra o hash
            if bcrypt.checkpw(password.encode("utf-8"), hash_do_banco):
                return user
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()
    return None

# ---------------------------------------------------------
# 3. LOGICA DE SINCRONIZAÇÃO DO USUÁRIO MASTER
# ---------------------------------------------------------
# Criamos o master apenas uma vez por sessão do servidor para performance
if 'master_verificado' not in st.session_state:
    try:
        MASTER_PASS = st.secrets.get("MASTER_PASSWORD", "m@ster26")
        # Esta função do db.py já ignora se o usuário já existir
        sucesso, msg = cadastrar_usuario_db("master", MASTER_PASS, "admin")
        
        if sucesso:
            print("✅ [Sistema] Usuário master garantido no banco.")
        st.session_state['master_verificado'] = True
    except Exception as e:
        print(f"⚠️ [Aviso] Verificação de master: {e}")

# ---------------------------------------------------------
# 4. INTERFACE DE LOGIN (UI)
# ---------------------------------------------------------
def login():
    """Renderiza a tela de login estilizada."""
    aplicar_estilo_fcj() 

    if "forgot_password" not in st.session_state:
        st.session_state.forgot_password = False
    
    # Logotipo FCJ
    col_logo_l, col_logo_c, col_logo_r = st.columns([1, 1.5, 1])
    with col_logo_c:
        # Caminho relativo considerando que Home.py chama login.py
        st.image("app/assets/logo_fcj.png", width="stretch")

    # Container central de acesso
    with st.container(border=True):
        if not st.session_state.forgot_password:
            st.markdown("<h3 style='text-align: center;'>Acesso à Plataforma</h3>", unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Usuário", placeholder="Digite seu usuário")
                password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
                submit = st.form_submit_button("Entrar", width="stretch", type="primary")
                
                if submit:
                    user = authenticate(username, password)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user["username"]
                        st.session_state["role"] = user["role"]
                        st.session_state["usuario_id"] = user["id"]
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha inválidos.")
            
            if st.button("Esqueci minha senha", width="stretch"):
                st.session_state.forgot_password = True
                st.rerun()
        
        else:
            # Interface de recuperação
            st.markdown("<h3 style='text-align: center;'>🔑 Recuperar Acesso</h3>", unsafe_allow_html=True)
            st.write("Sua solicitação será enviada para a administração da FCJ.")
            
            user_recup = st.text_input("Informe seu Usuário")
            
            if st.button("Enviar Solicitação", width="stretch", type="primary"):
                if user_recup:
                    if registrar_solicitacao_reset(user_recup):
                        st.success("✅ Solicitação enviada com sucesso!")
                    else:
                        st.error("❌ Falha ao registrar solicitação.")
                else:
                    st.warning("Preencha o campo de usuário.")

            if st.button("Voltar ao Login", width="stretch"):
                st.session_state.forgot_password = False
                st.rerun()

def logout():
    """Limpa a sessão e reinicia o app."""
    st.session_state.clear()
    st.rerun()