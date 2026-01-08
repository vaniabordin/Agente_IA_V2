import bcrypt
import mysql.connector
import pandas as pd
from mysql.connector import Error
import os
from datetime import datetime
import json
import streamlit as st

# ==========================================================
# 1. CONFIGURAÇÕES E CONEXÃO (TIDB CLOUD + STREAMLIT SECRETS)
# ==========================================================

def conectar(incluir_db=True):
    """
    Estabelece a conexão com o banco de dados.
    Busca as credenciais em st.secrets (Streamlit Cloud).
    """
    try:
        config = {                       
            "host": st.secrets["mysql"]["host"],
            "port": st.secrets["mysql"]["port"],
            "user": st.secrets["mysql"]["user"],
            "password": st.secrets["mysql"]["password"],            
            "use_pure": True,
            "ssl_verify_cert": False,  # CORREÇÃO para o erro SSL das imagens
            "connection_timeout": 20
        }        
        
        if incluir_db:
            config["database"] = st.secrets["mysql"]["database"]

        return mysql.connector.connect(**config)
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")
        return None

# Diretórios para arquivos (Caminhos relativos para Nuvem)
# Nota: No Streamlit Cloud, esses arquivos são temporários e somem após o reboot.
UPLOAD_DIR = "uploads/entregas_alunos"
IA_KNOWLEDGE_DIR = "knowledge_base"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(IA_KNOWLEDGE_DIR, exist_ok=True)

# ==========================================================
# 2. INFRAESTRUTURA (INIT DB)
# ==========================================================

def init_db():
    """Cria o banco e todas as tabelas necessárias no TiDB."""
    conn = conectar(incluir_db=True)
    if not conn:
        return
    

    try:
        with conn.cursor() as cur:
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
                    conteudo LONGTEXT,
                    descricao TEXT,
                    status VARCHAR(20) DEFAULT 'ativo',
                    data_subida DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. ARQUIVOS TEMPLATES (Modelos para baixar)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS arquivos_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome_formulario VARCHAR(100) NOT NULL,
                    template ENUM('Q1','Q2','Q3','Q4') NOT NULL,
                    nome_arquivo_original VARCHAR(255),
                    caminho_arquivo VARCHAR(500),
                    tipo_arquivo VARCHAR(500),
                    status VARCHAR(50) DEFAULT 'ativo',
                    data_upload DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. PROGRESSO DE ETAPAS
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
            
            # 7. RESPOSTAS DOS TEMPLATES
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
        conn.close()

# ==========================================================
# 3. GESTÃO DE USUÁRIOS
# ==========================================================

def cadastrar_usuario_db(username, password, role):
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, "⚠️ Este nome de usuário já está em uso."
            
            password_bytes = password.encode('utf-8')
            senha_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
            
            sql = "INSERT INTO usuarios (username, senha_hash, role, ativo) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (username, senha_hash, role, True))
            
            conn.commit()
            return True, f"✅ Usuário {username} cadastrado!"
        except Error as e:
            return False, f"❌ Erro: {e}"
        finally:
            cursor.close()
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
            cursor.close()
            conn.close()

# ==========================================================
# 4. GESTÃO DE PROGRESSO E ENTREGAS
# ==========================================================

def verificar_etapa_concluida(usuario_id, nome_formulario):
    conn = conectar()
    concluido = False
    if conn:
        try:
            cur = conn.cursor()
            query = "SELECT id FROM progresso_etapas WHERE usuario_id = %s AND TRIM(nome_etapa) = %s LIMIT 1"
            cur.execute(query, (usuario_id, nome_formulario.strip()))
            if cur.fetchone():
                concluido = True
        except Error as e:
            print(f"Erro ao verificar etapa: {e}")
        finally:
            cur.close()
            conn.close()
    return concluido

def salvar_conclusao_etapa(usuario_id, nome_etapa):
    """Registra que o usuário finalizou uma etapa específica."""
    conn = conectar()
    if not conn: return False
    try:
        cursor = conn.cursor()
        query = "INSERT IGNORE INTO progresso_etapas (usuario_id, nome_etapa) VALUES (%s, %s)"
        cursor.execute(query, (usuario_id, nome_etapa.strip()))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao salvar progresso: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def salvar_entrega_e_feedback(usuario_id, etapa, arquivo_objeto, feedback_json):
    """Salva o arquivo do aluno e o parecer da IA no banco."""
    conn = conectar()
    if not conn: return False
    
    cursor = conn.cursor()
    try:
        # Gerar nome único para evitar sobreposição na nuvem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_limpo = "".join(c for c in arquivo_objeto.name if c.isalnum() or c in "._-").strip()
        nome_unico = f"user_{usuario_id}_{timestamp}_{nome_limpo}"
        
        # Caminho relativo para salvar o arquivo físico
        caminho_relativo = os.path.join(UPLOAD_DIR, nome_unico)

        # Escrita física do arquivo
        with open(caminho_relativo, "wb") as f:
            f.write(arquivo_objeto.getbuffer())

        if isinstance(feedback_json, str):
            feedback_json = json.loads(feedback_json)
        
        perguntas_str = json.dumps(feedback_json.get('perguntas_faltantes', []))
        dicas_str = feedback_json.get('dicas', '')
        
        # Salvamos o caminho_relativo para que funcione em qualquer sistema
        query = """
            INSERT INTO avaliacoes_ia 
            (usuario_id, etapa, caminho_arquivo_aluno, nome_arquivo_original, 
             porcentagem, zona, feedback_ludico, cor, perguntas_faltantes, dicas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            usuario_id, etapa.strip(), caminho_relativo, arquivo_objeto.name,
            feedback_json.get('porcentagem', 0), feedback_json.get('zona', 'N/A'), 
            feedback_json.get('feedback_ludico', ''), feedback_json.get('cor', '#FFFFFF'),
            perguntas_str, dicas_str
        ))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"❌ Erro ao salvar entrega: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# ==========================================================
# 5. CONSULTAS IA E FEEDBACK
# ==========================================================
def buscar_ultimo_feedback_ia(usuario_id, etapa=None):
    conn = conectar()
    if not conn:
        return None
    
    cur = None # Inicializa para evitar erro no finally
    try:
        cur = conn.cursor(dictionary=True)
        
        if etapa is None:
            query = "SELECT * FROM avaliacoes_ia WHERE usuario_id = %s ORDER BY data_avaliacao DESC LIMIT 1"
            cur.execute(query, (usuario_id,))
        else:
            query = "SELECT * FROM avaliacoes_ia WHERE usuario_id = %s AND TRIM(etapa) = %s ORDER BY data_avaliacao DESC LIMIT 1"
            cur.execute(query, (usuario_id, etapa.strip()))
        
        res = cur.fetchone()
        
        if res and res.get('perguntas_faltantes'):
            try:
                # Tenta converter o texto do banco de volta para lista
                if isinstance(res['perguntas_faltantes'], str):
                    res['perguntas_faltantes'] = json.loads(res['perguntas_faltantes'])
            except (json.JSONDecodeError, TypeError):
                res['perguntas_faltantes'] = []
        return res 
    except Exception as e:
        print(f"❌ Erro ao buscar último feedback: {e}")
        return None
    
    finally:
        if cur:
            cur.close()
        conn.close()

def buscar_envios_startups():
    """Retorna todos os envios de alunos para o painel administrativo."""
    conn = conectar()
    if conn:
        try:
            # Esta query busca os dados da entrega e o nome do usuário que enviou
            query = """
                SELECT a.id, u.username, a.etapa, a.porcentagem, a.data_avaliacao, a.caminho_arquivo_aluno 
                FROM avaliacoes_ia a
                JOIN usuarios u ON a.usuario_id = u.id
                ORDER BY a.data_avaliacao DESC
            """
            return pd.read_sql(query, conn)
        except Exception as e:
            print(f"Erro ao buscar envios: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

def buscar_usuario_id(username):
    """Auxiliar para encontrar o ID de um usuário pelo nome."""
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            res = cursor.fetchone()
            return res[0] if res else None
        finally:
            conn.close()
    return None


def registrar_erro_ia(usuario_id, etapa, tipo_erro, mensagem):

    conn = conectar()
    if not conn: return False
    
    cursor = conn.cursor()
    if conn:
        try:            
            query = "INSERT INTO logs_erros_ia (usuario_id, etapa, tipo_erro, mensagem_erro) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (usuario_id, etapa, tipo_erro, mensagem))
            conn.commit()

        finally:
            cursor.close()
            conn.close()

# ==========================================================

# 6. GESTÃO DE TEMPLATES E RELATÓRIOS

# ==========================================================

def excluir_template(id_template):
    """Remove um template do banco de dados com tratamento de erro e fechamento seguro."""
    conn = conectar()
    if not conn: 
        return False
    
    cur = conn.cursor()
    try:
        # Executa a remoção
        cur.execute("DELETE FROM arquivos_templates WHERE id = %s", (id_template,))
        conn.commit()
        return True
    except Exception as e:
        # Em caso de erro, desfaz qualquer alteração pendente e loga o erro
        conn.rollback()
        print(f"❌ Erro ao excluir template {id_template}: {e}")
        return False
    finally:
        # O bloco 'finally' garante que o fechamento ocorra mesmo se houver erro
        cur.close()
        conn.close()

# ==========================================================

# 7. CONHECIMENTO DA IA

# ==========================================================
def buscar_conhecimento_ia(termo_busca):
    conn = conectar()
    if not conn: 
        return ""

    # Definimos o cursor como None inicialmente para o finally não dar erro
    cursor = None 
    try:
        cursor = conn.cursor(dictionary=True)

        # 1. Limpeza e preparação do termo
        termo = f"%{termo_busca.strip()}%"

        # 2. Execução da busca limitada a 3 resultados para performance
        query = """
            SELECT conteudo FROM ia_conhecimento 
            WHERE status = 'ativo' AND (conteudo LIKE %s OR nome LIKE %s) 
            LIMIT 3
        """
        cursor.execute(query, (termo, termo))
        resultados = cursor.fetchall()       

        if not resultados:
            return ""

        # 3. Join dos conteúdos encontrados para servir de contexto à IA
        contexto = "\n---\n".join([r['conteudo'] for r in resultados if r['conteudo']])
        return contexto

    except Exception as e:
        print(f"❌ Erro ao buscar conhecimento: {e}")
        return ""
    finally:
        # Fechamento seguro de ambos os recursos
        if cursor:
            cursor.close()
        conn.close()
        
# -------------------------
# Conhecimento da IA 
#--------------------------
def registrar_no_banco(nome, tipo, caminho, descricao, texto_extraido):
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            sql = """INSERT INTO ia_conhecimento 
                     (nome, tipo_conteudo, caminho_ou_url, conteudo, descricao, status) 
                     VALUES (%s, %s, %s, %s, %s, 'ativo')"""
            cursor.execute(sql, (nome, tipo, caminho, texto_extraido, descricao))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Erro ao salvar no banco: {e}")
            return False
        finally:
            conn.close()
    return False

def consultar_base_ativa():
    conn = conectar()
    if conn:
        try:
            query = "SELECT id, nome, tipo_conteudo, caminho_ou_url, descricao, data_subida FROM ia_conhecimento ORDER BY id DESC"
            # Usando context manager para evitar avisos do pandas
            return pd.read_sql(query, conn)
        except Exception as e:
            st.error(f"Erro ao consultar banco: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

def deletar_material_db(id_db):
    conn = conectar()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ia_conhecimento WHERE id = %s", (id_db,))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Erro ao deletar no banco: {e}")
            return False
        finally:
            conn.close()
    return False

# ---------------------------------
# Gerenciado - Cria Templates
# ---------------------------------
def salvar_template_db(nome_form, trimestre, arquivo_objeto, id_editando=None):
    """Gerencia a inserção e atualização de templates no banco."""
    conn = conectar()
    if not conn: return False
    try:
        cursor = conn.cursor()
        caminho_final_banco = None # Variável para armazenar o caminho formatado
        
        # 1. Se houver um novo arquivo, salva fisicamente
        if arquivo_objeto:
            # AJUSTE: Pasta alinhada com as páginas de Trimestre
            pasta_destino = os.path.join("assets", "templates")
            if not os.path.exists(pasta_destino): 
                os.makedirs(pasta_destino)
            
            nome_unico = f"{datetime.now().strftime('%Y%m%d%H%M')}_{arquivo_objeto.name}"
            caminho_fisico = os.path.join(pasta_destino, nome_unico)
            
            # AJUSTE: Caminho formatado para o Banco (compatível com Linux/Nuvem)
            caminho_final_banco = caminho_fisico.replace("\\", "/")
            
            with open(caminho_fisico, "wb") as f:
                f.write(arquivo_objeto.read())

        # 2. Lógica de UPDATE ou INSERT
        if id_editando:
            if arquivo_objeto:
                # AJUSTE: Usando caminho_final_banco no SQL
                sql = """UPDATE arquivos_templates 
                        SET nome_formulario=%s, template=%s, nome_arquivo_original=%s, 
                            caminho_arquivo=%s, tipo_arquivo=%s, data_upload=NOW()
                        WHERE id=%s"""
                cursor.execute(sql, (nome_form, trimestre, arquivo_objeto.name, 
                                     caminho_final_banco, arquivo_objeto.type, id_editando))
            else:
                sql = "UPDATE arquivos_templates SET nome_formulario=%s, template=%s WHERE id=%s"
                cursor.execute(sql, (nome_form, trimestre, id_editando))
        else:
            if not arquivo_objeto: return False
            # AJUSTE: Usando caminho_final_banco no SQL
            sql = """INSERT INTO arquivos_templates 
                    (nome_formulario, template, nome_arquivo_original, caminho_arquivo, tipo_arquivo, status, data_upload) 
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())"""
            cursor.execute(sql, (nome_form, trimestre, arquivo_objeto.name, 
                                 caminho_final_banco, arquivo_objeto.type, "ativo"))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro no banco: {e}")
        return False
    finally:
        conn.close()

def listar_templates_db():
    """Retorna o DataFrame de templates ativos."""
    conn = conectar()
    if conn:
        try:
            return pd.read_sql("SELECT id, nome_formulario, template, nome_arquivo_original, caminho_arquivo, status FROM arquivos_templates ORDER BY template ASC, id DESC", conn)
        finally:
            conn.close()
    return pd.DataFrame()