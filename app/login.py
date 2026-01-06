import streamlit as st
import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv
from utils.ui import aplicar_estilo_fcj
from utils.db import cadastrar_usuario_db

load_dotenv()

# --------------------------------
# CONEXÃO COM MYSQL
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

# --------------------------------
# REGISTRO DE SOLICITAÇÃO (BANCO)
# --------------------------------
def registrar_solicitacao_reset(identificador):
    conn = get_connection()
    if conn:
        try:
            cursor = conn.cursor()
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
            return False
        finally:
            conn.close()
    return False

# --------------------------------
# AUTENTICAÇÃO
# --------------------------------
def authenticate(username, password):
    conn = get_connection()
    if not conn:
        return None

    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, username, senha_hash, role, ativo FROM usuarios WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and user["ativo"]:
        hash_do_banco = user["senha_hash"]
        if isinstance(hash_do_banco, str):
            hash_do_banco = hash_do_banco.encode("utf-8")

        if bcrypt.checkpw(password.encode("utf-8"), hash_do_banco):
            return user
    return None

# ==========================================================
# RECUPERAÇÃO DE ACESSO (Preparado para Banco Local/Online)
# ==========================================================
try:
    # Cadastrar o master. 
    # A função cadastrar_usuario_db já retorna (False, "mensagem") 
    # se o usuário existir, então o código não trava.
    MASTER_PASS = os.getenv("MASTER_PASSWORD", "m@ster26")
   
    sucesso, msg = cadastrar_usuario_db("master", MASTER_PASS, "admin")
    
    if sucesso:
        print("✅ Usuário master criado pela primeira vez.")
    else:
        # Se caiu aqui, é porque o usuário já existe ou houve erro de conexão
        pass 
except Exception as e:
    # Log de erro silencioso para não assustar o usuário na interface
    print(f"Aviso: O usuário master não pôde ser verificado/criado: {e}")

# --------------------------------
# LOGIN UI
# --------------------------------
def login():
   # Aplica o CSS carregado do arquivo assets/style.css
    aplicar_estilo_fcj() 

    if "forgot_password" not in st.session_state:
        st.session_state.forgot_password = False
    
    # Centraliza o logotipo da FCJ
    col_logo_l, col_logo_c, col_logo_r = st.columns([1, 1.5, 1])
    with col_logo_c:
        # Use o caminho correto para sua logo
        st.image("app/assets/logo_fcj.png", use_container_width=True)

    # Container da Caixa de Login
    with st.container(border=True):
        if not st.session_state.forgot_password:
            st.markdown("<h3 class='login-header'> Acesso à Plataforma</h3>", unsafe_allow_html=True)
            
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Usuário", placeholder="Seu nome de usuário")
                password = st.text_input("Senha", type="password", placeholder="Sua senha secreta")
                submit = st.form_submit_button("Entrar", use_container_width=True, type="primary")
                
                if submit:
                    user = authenticate(username, password)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user["username"]
                        st.session_state["role"] = user["role"]
                        st.session_state["usuario_id"] = user["id"]
                        st.rerun()
                    else:
                        st.error("Usuário ou senha inválidos.")
            
            # O botão de esqueci senha deve ficar FORA do formulário          
            if st.button("Esqueci minha senha", use_container_width=True, type="secondary"):
                st.session_state.forgot_password = True
                st.rerun()
        
        else:
            st.markdown("<h3 class='login-header'>🔑 Solicitar Nova Senha</h3>", unsafe_allow_html=True)
            st.info("Sua solicitação será enviada para a equipe de administração da FCJ.")
            
            user_recup = st.text_input("Informe seu Usuário ou E-mail")
            
            if st.button("Enviar Solicitação", use_container_width=True, type="primary"):
                if user_recup:
                    if registrar_solicitacao_reset(user_recup):
                        st.success("✅ Enviado! O administrador entrará em contato.")
                    else:
                        st.error("❌ Erro ao registrar. Tente novamente.")
                else:
                    st.warning("Por favor, preencha o campo acima.")

            if st.button("Voltar ao Login", use_container_width=True, type="secondary"):
                st.session_state.forgot_password = False
                st.rerun()

# --------------------------------
# LOGOUT
# --------------------------------
def logout():
    st.session_state.clear()
    st.rerun()