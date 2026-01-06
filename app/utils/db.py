import bcrypt
import mysql.connector
import pandas as pd
from mysql.connector import Error
import os
from datetime import datetime
import json
import streamlit as st

# ==========================================================
# 1. CONFIGURAÇÕES E DIRETÓRIOS
# ==========================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "db_avaliacoes_ia"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", "root"),
}

# Caminhos Absolutos para evitar erros de execução
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "uploads", "entregas_alunos")
IA_KNOWLEDGE_DIR = os.path.join(BASE_DIR, "..", "knowledge_base")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IA_KNOWLEDGE_DIR, exist_ok=True)

# ==========================================================
# 2. CONEXÃO E INFRAESTRUTURA (INIT)
# ==========================================================

def conectar(incluir_db=True):
    try:
        config = DB_CONFIG.copy()
        if not incluir_db:
            config.pop("database", None)
        return mysql.connector.connect(**config)
    except Error as e:
        st.error(f"❌ Erro de conexão com MySQL: {e}")
        return None

def init_db():
    """Cria o banco e todas as tabelas necessárias."""
    conn_raw = conectar(incluir_db=False)
    if conn_raw:
        cur = conn_raw.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cur.close()
        conn_raw.close()

    conn = conectar()
    if not conn: return

    cur = conn.cursor()
    try:
        # 1. USUÁRIOS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                senha_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
       
        # 2. BASE DE CONHECIMENTO IA
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ia_conhecimento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                tipo_conteudo ENUM('arquivo', 'youtube') NOT NULL,
                caminho_ou_url VARCHAR(500) NOT NULL,
                conteudo LONGTEXT,  -- Campo onde ficará o texto para a IA ler
                descricao TEXT,
                status VARCHAR(20) DEFAULT 'ativo', -- Adicionado para o filtro da busca
                data_subida DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. ARQUIVOS TEMPLATES (Modelos para download)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS arquivos_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nome_formulario VARCHAR(100) NOT NULL,
                template ENUM('Q1','Q2','Q3','Q4') NOT NULL,
                nome_arquivo_original VARCHAR(255),
                caminho_arquivo VARCHAR(500),
                tipo_arquivo VARCHAR(255),
                status VARCHAR(50) DEFAULT 'ativo',
                data_upload DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. PROGRESSO DE ETAPAS (Coração do desbloqueio)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS progresso_etapas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                nome_etapa VARCHAR(100) NOT NULL,
                status VARCHAR(20) DEFAULT 'Concluído',
                data_conclusao DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_user_etapa (usuario_id, nome_etapa),
                CONSTRAINT fk_progresso_user FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        
        # 5. AVALIAÇÕES IA (Entregas dos alunos)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS avaliacoes_ia (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                etapa VARCHAR(100) NOT NULL,
                caminho_arquivo_aluno VARCHAR(500),
                nome_arquivo_original VARCHAR(255),
                porcentagem INT,
                zona VARCHAR(50),
                feedback_ludico TEXT,
                cor VARCHAR(20),
                perguntas_faltantes TEXT, 
                dicas TEXT,               
                data_avaliacao DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_aval_ia_user FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        
        # 6. LOGS DE ERROS
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs_erros_ia (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT,
                etapa VARCHAR(100),
                tipo_erro VARCHAR(100),
                mensagem_erro TEXT,
                data_erro DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_log_user FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        
            # 7. RESPOSTAS DOS TEMPLATES (Tabela que estava faltando)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS respostas_templates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario_id INT NOT NULL,
                arquivo_id INT NOT NULL,
                respostas JSON,
                data_preenchimento DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_resp_user FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                CONSTRAINT fk_resp_arquivo FOREIGN KEY (arquivo_id) REFERENCES arquivos_templates(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()        
    except Error as e:
        conn.rollback()
        st.error(f"❌ Erro ao inicializar banco: {e}")
    finally:
        cur.close()
        conn.close()

# ==========================================================
# 3. GESTÃO DE USUÁRIOS (ADMIN)
# ==========================================================
def cadastrar_usuario_db(username, password, role):
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, "⚠️ Este nome de usuário já está em uso."
            
            # --- CRIPTOGRAFIA ---
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt()
            senha_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
            
            # Note que agora passamos 'senha_hash' no lugar de 'password'
            sql = "INSERT INTO usuarios (username, senha_hash, role, ativo) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (username, senha_hash, role, True))
            
            conn.commit()
            return True, f"✅ Usuário {username} cadastrado com sucesso!"
        except Error as e:
            return False, f"❌ Erro ao cadastrar no banco: {e}"
        finally:
            conn.close()
    return False, "❌ Falha na conexão."

def remover_usuario_db(user_id, username):
    if username == "master":
        st.error("O usuário 'master' não pode ser removido.")
        return

    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
            conn.commit()
            st.toast(f"Usuário {username} removido!")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao deletar: {e}")
        finally:
            conn.close()


# ==========================================================
# 4. GESTÃO DE PROGRESSO E DESBLOQUEIO
# ==========================================================

def verificar_etapa_concluida(usuario_id, nome_formulario):
    """Verifica se a etapa anterior foi finalizada para liberar a próxima."""
    conn = conectar()
    concluido = False
    if conn:
        try:
            cur = conn.cursor()
            # TRIM garante que espaços extras não quebrem a lógica
            query = "SELECT id FROM progresso_etapas WHERE usuario_id = %s AND TRIM(nome_etapa) = %s LIMIT 1"
            cur.execute(query, (usuario_id, nome_formulario.strip()))
            if cur.fetchone():
                concluido = True
        except Error as e:
            print(f"Erro ao verificar etapa: {e}")
        finally:
            conn.close()
    return concluido

def salvar_conclusao_etapa(usuario_id, nome_etapa):
    """Marca uma etapa como 'Concluído' no banco."""
    conn = conectar()
    if conn:
        try:
            cur = conn.cursor()
            query = """
                INSERT INTO progresso_etapas (usuario_id, nome_etapa, status) 
                VALUES (%s, %s, 'Concluído')
                ON DUPLICATE KEY UPDATE 
                    status = 'Concluído',
                    data_conclusao = CURRENT_TIMESTAMP
            """
            cur.execute(query, (usuario_id, nome_etapa.strip()))
            conn.commit()
            return True
        except Error as e:
            print(f"Erro ao salvar progresso: {e}")
            return False
        finally:
            conn.close()
    return False

# ==========================================================
# 5. GESTÃO DE ENTREGAS E IA
# ==========================================================

def salvar_entrega_e_feedback(usuario_id, etapa, arquivo_objeto, feedback_json):
    """Salva o arquivo físico do aluno e o feedback gerado pela IA."""
    conn = conectar()
    if not conn: return False
    
    try:
        # 1. Nome de arquivo seguro
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_limpo = "".join(c for c in arquivo_objeto.name if c.isalnum() or c in "._-").strip()
        nome_unico = f"user_{usuario_id}_{timestamp}_{nome_limpo}"
        caminho_completo = os.path.join(UPLOAD_DIR, nome_unico)

        # 2. Escrita física
        with open(caminho_completo, "wb") as f:
            f.write(arquivo_objeto.getbuffer())

        # 3. Inserção no banco
        if isinstance(feedback_json, str):
            feedback_json = json.loads(feedback_json)
        
        # Converter lista de perguntas faltantes em string JSON para o banco
        perguntas_str = json.dumps(feedback_json.get('perguntas_faltantes', []))
        dicas_str = feedback_json.get('dicas', '')

        cursor = conn.cursor()
        query = """
            INSERT INTO avaliacoes_ia 
            (usuario_id, etapa, caminho_arquivo_aluno, nome_arquivo_original, 
             porcentagem, zona, feedback_ludico, cor, perguntas_faltantes, dicas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            usuario_id, etapa.strip(), caminho_completo, arquivo_objeto.name,
            feedback_json.get('porcentagem', 0), 
            feedback_json.get('zona', 'N/A'), 
            feedback_json.get('feedback_ludico', ''), 
            feedback_json.get('cor', '#FFFFFF'),
            perguntas_str,  
            dicas_str       
        )
        cursor.execute(query, valores)
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Erro em salvar_entrega_e_feedback: {e}")
        return False
    finally:
        conn.close()

def buscar_ultimo_feedback_ia(usuario_id, etapa=None):
    """Recupera a última análise da IA para exibir no dashboard, incluindo novos campos."""
    conn = conectar()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            
            # Caso a etapa não seja informada
            if etapa is None:
                query = """
                    SELECT porcentagem, zona, feedback_ludico, cor, data_avaliacao, 
                           perguntas_faltantes, dicas 
                    FROM avaliacoes_ia 
                    WHERE usuario_id = %s 
                    ORDER BY data_avaliacao DESC LIMIT 1
                """
                cur.execute(query, (usuario_id,))
            else:
                # Caso a etapa seja informada
                query = """
                    SELECT porcentagem, zona, feedback_ludico, cor, data_avaliacao, 
                           perguntas_faltantes, dicas 
                    FROM avaliacoes_ia 
                    WHERE usuario_id = %s AND TRIM(etapa) = %s 
                    ORDER BY data_avaliacao DESC LIMIT 1
                """
                cur.execute(query, (usuario_id, etapa.strip()))
            
            res = cur.fetchone()
            
            # Tratamento para converter o texto do banco em lista novamente
            if res and res.get('perguntas_faltantes'):
                try:
                    # Se salvou como string/JSON no banco, aqui garante que volte a ser lista
                    if isinstance(res['perguntas_faltantes'], str):
                        res['perguntas_faltantes'] = json.loads(res['perguntas_faltantes'])
                except:
                    # Se não for um JSON válido, transforma em lista simples por precaução
                    res['perguntas_faltantes'] = [res['perguntas_faltantes']]
            
            return res
        finally:
            conn.close()
    return None

def registrar_erro_ia(usuario_id, etapa, tipo_erro, mensagem):
    conn = conectar()
    if conn:
        try:
            cur = conn.cursor()
            query = "INSERT INTO logs_erros_ia (usuario_id, etapa, tipo_erro, mensagem_erro) VALUES (%s, %s, %s, %s)"
            cur.execute(query, (usuario_id, etapa, tipo_erro, mensagem))
            conn.commit()
        finally:
            conn.close()

# ==========================================================
# 6. GESTÃO DE TEMPLATES E RELATÓRIOS
# ==========================================================

def excluir_template(id_template):
    conn = conectar()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM arquivos_templates WHERE id = %s", (id_template,))
        conn.commit()
        conn.close()
        return True
    return False

def buscar_envios_startups():
    conn = conectar()
    if conn:
        try:
            query = """
                SELECT u.username, r.data_preenchimento, a.nome_formulario, r.respostas
                FROM respostas_templates r
                JOIN usuarios u ON r.usuario_id = u.id
                JOIN arquivos_templates a ON r.arquivo_id = a.id
                ORDER BY r.data_preenchimento DESC
            """
            return pd.read_sql(query, conn)
        finally:
            conn.close()
    return pd.DataFrame()

# ==========================================================
# 7. CONHECIMENTO DA IA
# ==========================================================
def buscar_conhecimento_ia(termo_busca):
    conn = conectar()
    if not conn: return ""
    try:
        cursor = conn.cursor(dictionary=True)
        # 1. Limpamos o termo para evitar caracteres que quebrem o LIKE
        termo = f"%{termo_busca.strip()}%"
        
        # 2. Buscamos no conteúdo (LONGTEXT) que foi processado no upload
        query = "SELECT conteudo FROM ia_conhecimento WHERE status = 'ativo' AND (conteudo LIKE %s OR nome LIKE %s) LIMIT 3"
        cursor.execute(query, (termo, termo))
        resultados = cursor.fetchall()
        
        if not resultados:
            return ""

        contexto = "\n---\n".join([r['conteudo'] for r in resultados if r['conteudo']])
        return contexto
    except Exception as e:
        print(f"Erro ao buscar conhecimento: {e}")
        return ""
    finally:
        conn.close()