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
    """Estabelece a conexão com o banco de dados via st.secrets para INSERT/UPDATE."""
    try:
        config = {                       
            "host": st.secrets["mysql"]["host"],
            "port": st.secrets["mysql"]["port"],
            "user": st.secrets["mysql"]["user"],
            "password": st.secrets["mysql"]["password"],            
            "use_pure": True,            
            "ssl_verify_cert": False,
            "ssl_disabled": False,
            "connection_timeout": 20
        }        
        config["ssl_ca"] = None  # Usa os certificados do sistema
        
        if incluir_db:
            config["database"] = st.secrets["mysql"]["database"]
            
        return mysql.connector.connect(**config)
    except Exception as e:
        st.error(f"Erro ao conectar no banco (Driver): {e}")
        return None

# --- LÓGICA DE CAMINHOS TÉCNICOs---
RAIZ_PROJETO = os.getcwd()
UPLOAD_DIR = os.path.join(RAIZ_PROJETO, "uploads", "entregas_alunos")
IA_KNOWLEDGE_DIR = os.path.join(RAIZ_PROJETO, "knowledge_base")
TEMPLATES_DIR = os.path.join(RAIZ_PROJETO, "assets_global", "templates")

# Garante a existência das pastas
for folder in [UPLOAD_DIR, IA_KNOWLEDGE_DIR, TEMPLATES_DIR]:
    os.makedirs(folder, exist_ok=True)

# ==========================================================
# 2. INFRAESTRUTURA (INIT DB)
# ==========================================================

def init_db():
    """Cria o banco e todas as tabelas necessárias no TiDB."""
    conn = conectar(incluir_db=True)
    if not conn: return
    try:
        with conn.cursor() as cur:
            # Aqui devem estar seus comandos CREATE TABLE IF NOT EXISTS
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
        cursor = None
        try:
            cursor = conn.cursor()
            # 1. Verifica se usuário já existe
            cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
            if cursor.fetchone():
                return False, "⚠️ Este nome de usuário já está em uso."
            
            # 2. Hashing da senha (Segurança)
            password_bytes = password.encode('utf-8')
            senha_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
            
            # 3. Inserção
            sql = "INSERT INTO usuarios (username, senha_hash, role, ativo) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (username, senha_hash, role, True))
            conn.commit()
            return True, f"✅ Usuário {username} cadastrado!"
        except Exception as e:
            return False, f"❌ Erro no banco: {e}"
        finally:
            if cursor: cursor.close()
            conn.close()
    return False, "❌ Falha na conexão com o banco."

def remover_usuario_db(user_id, username):
    # Trava de segurança para o administrador principal
    if username.lower() == "master":
        st.error("O usuário 'master' não pode ser removido por questões de segurança.")
        return False
        
    conn = conectar()
    if conn:
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usuarios WHERE id = %s", (user_id,))
            conn.commit()
            st.toast(f"👤 Usuário {username} removido com sucesso!")
            return True
        except Exception as e:
            st.error(f"Erro ao deletar usuário: {e}")
            return False
        finally:
            if cursor: cursor.close()
            conn.close()
    return False

# ==========================================================
# 4. GESTÃO DE PROGRESSO E ENTREGAS
# ==========================================================

def verificar_etapa_concluida(usuario_id, nome_formulario):
    conn = conectar()
    concluido = False
    cursor = None # Inicialização de segurança
    if conn:
        try:
            cursor = conn.cursor()
            query = "SELECT id FROM progresso_etapas WHERE usuario_id = %s AND TRIM(nome_etapa) = %s LIMIT 1"
            cursor.execute(query, (usuario_id, nome_formulario.strip()))
            if cursor.fetchone():
                concluido = True
        except Exception as e:
            print(f"Erro ao verificar etapa: {e}")            
        finally:
            if cursor: cursor.close()
            conn.close()
    return concluido

def salvar_conclusao_etapa(usuario_id, nome_etapa):
    conn = conectar()
    if not conn: return False
    cursor = None
    try:
        cursor = conn.cursor()
        # INSERT IGNORE evita duplicatas sem gerar erro no banco
        query = "INSERT IGNORE INTO progresso_etapas (usuario_id, nome_etapa) VALUES (%s, %s)"
        cursor.execute(query, (usuario_id, nome_etapa.strip()))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao salvar progresso: {e}")
        return False
    finally:
        if cursor: cursor.close()
        conn.close()

def salvar_entrega_e_feedback(usuario_id, etapa, arquivo_objeto, feedback_json):
    """Salva o arquivo do aluno e o parecer da IA no banco e no disco."""
    conn = conectar()
    if not conn: return False
    cursor = None
    
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")               
        
        # Limpeza do nome do arquivo (White-listing de caracteres)
        nome_original = os.path.basename(arquivo_objeto.name)
        nome_limpo = "".join(c for c in nome_original if c.isalnum() or c in "._-").strip()
        nome_unico = f"user_{usuario_id}_{timestamp}_{nome_limpo}"
        
        # Caminho físico para escrita no servidor
        caminho_fisico = os.path.join(UPLOAD_DIR, nome_unico)
                
        # Gravação do arquivo binário
        with open(caminho_fisico, "wb") as f:
            f.write(arquivo_objeto.getbuffer())
        
        # Caminho relativo para consulta futura
        caminho_banco = f"uploads/entregas_alunos/{nome_unico}"
                               
        # Sanitização do JSON retornado pela IA
        if isinstance(feedback_json, str):          
            try:
                # Remove blocos de código markdown que a IA costuma incluir
                feedback_limpo = feedback_json.replace("```json", "").replace("```", "").strip()
                feedback_json = json.loads(feedback_limpo)
            except Exception:
                # Fallback caso o JSON seja realmente inválido
                feedback_json = {
                    "porcentagem": 0, 
                    "zona": "Erro de Formatação", 
                    "feedback_ludico": "A IA gerou um formato inconsistente.",
                    "dicas": feedback_json 
                }
        
        # Extração segura com valores default (evita KeyError)
        porcentagem = feedback_json.get('porcentagem', 0)
        zona = feedback_json.get('zona', 'Análise Pendente')
        feedback_ludico = feedback_json.get('feedback_ludico', 'Sem parecer disponível.')
        cor = feedback_json.get('cor', '#808080')
        
        perguntas_faltantes = feedback_json.get('perguntas_faltantes', [])
        # Serializamos a lista em string para salvar no campo TEXT do banco
        perguntas_str = json.dumps(perguntas_faltantes)
        dicas_str = feedback_json.get('dicas', '')
        
        query = """
            INSERT INTO avaliacoes_ia 
            (usuario_id, etapa, caminho_arquivo_aluno, nome_arquivo_original, 
             porcentagem, zona, feedback_ludico, cor, perguntas_faltantes, dicas)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            usuario_id, etapa.strip(), caminho_banco, nome_original,
            porcentagem, zona, feedback_ludico, cor, perguntas_str, dicas_str
        ))
        
        conn.commit()
        return True    
    except Exception as e:
        st.error(f"❌ Erro crítico ao salvar entrega: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
# ==========================================================
# 5. CONSULTAS IA E FEEDBACK
# ==========================================================

def buscar_ultimo_feedback_ia(usuario_id, etapa=None):
    conn = conectar()
    if not conn: return None
    cur = None 
    try:
        cur = conn.cursor(dictionary=True)
        if etapa is None:
            query = "SELECT * FROM avaliacoes_ia WHERE usuario_id = %s ORDER BY data_avaliacao DESC LIMIT 1"
            cur.execute(query, (usuario_id,))
        else:
            query = "SELECT * FROM avaliacoes_ia WHERE usuario_id = %s AND TRIM(etapa) = %s ORDER BY data_avaliacao DESC LIMIT 1"
            cur.execute(query, (usuario_id, etapa.strip()))
        
        res = cur.fetchone()
        
        # Se encontrou resultado, trata o campo JSON das perguntas faltantes
        if res and res.get('perguntas_faltantes'):
            try:
                if isinstance(res['perguntas_faltantes'], str):
                    res['perguntas_faltantes'] = json.loads(res['perguntas_faltantes'])
            except (json.JSONDecodeError, TypeError):
                res['perguntas_faltantes'] = []
        
        return res 
    except Exception as e:
        # Usar st.error aqui é opcional, mas ajuda no debug durante o desenvolvimento
        print(f"❌ Erro ao buscar último feedback: {e}")
        return None
    finally:
        if cur: 
            cur.close()
        if conn: # Verificação adicional de segurança
            conn.close()

def buscar_envios_startups():
    conn = conectar()
    if not conn:
        return pd.DataFrame()
    try:      
        query = """
            SELECT a.id, u.username, a.etapa, a.porcentagem, a.data_avaliacao, a.caminho_arquivo_aluno 
            FROM avaliacoes_ia a
            JOIN usuarios u ON a.usuario_id = u.id
            ORDER BY a.data_avaliacao DESC
        """
        # O pandas já cuida de abrir o cursor, ler os dados e fechar o cursor internamente
        df = pd.read_sql(query, conn) 
        return df
    except Exception as e:
        st.error(f"Erro ao buscar envios: {e}")
        return pd.DataFrame()
    finally:
        # Fechamos apenas a conexão, pois o pandas/sqlalchemy gerencia o resto
        if conn:
            conn.close()

def buscar_usuario_id(username):
    conn = conectar()
    if not conn:
        return None
    
    cursor = None # Inicializa para evitar erro no finally
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
        res = cursor.fetchone()
        
        # res é uma tupla, ex: (12,) -> res[0] retorna 12
        return res[0] if res else None
        
    except Exception as e:
        print(f"❌ Erro ao buscar ID do usuário: {e}")
        return None
    finally:
        if cursor: 
            cursor.close()
        conn.close()

def registrar_erro_ia(usuario_id, etapa, tipo_erro, mensagem):
    conn = conectar()
    if not conn: 
        return False
    
    cursor = None
    try:            
        cursor = conn.cursor()
        # Garantimos que a mensagem seja string e limitamos o tamanho para não estourar o campo no banco
        mensagem_segura = str(mensagem)[:1000] 
        
        query = "INSERT INTO logs_erros_ia (usuario_id, etapa, tipo_erro, mensagem_erro) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (usuario_id, etapa, tipo_erro, mensagem_segura))
        conn.commit()
        return True
    except Exception as e:
        # Se falhar aqui, imprimimos no console do servidor para não entrar em loop de erro
        print(f"❌ Falha crítica ao registrar log de erro no banco: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        conn.close()

# ==========================================================
# 6. GESTÃO DE TEMPLATES
# ==========================================================
def excluir_template(id_template):
    conn = conectar()
    if not conn: return False
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM arquivos_templates WHERE id = %s", (id_template,))
        conn.commit()
        return True
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Erro ao excluir template {id_template}: {e}")
        return False
    finally:
        if cur: cur.close()
        if conn: conn.close()

def salvar_template_db(nome_form, trimestre, arquivo_objeto, id_editando=None):
    """Gerencia a inserção e atualização de templates (Arquivos de Referência)."""
    conn = conectar()
    if not conn: return False
    cursor = None
    try:
        cursor = conn.cursor()
        caminho_final_banco = None 
        
        # Se um novo arquivo foi enviado no upload
        if arquivo_objeto:
            nome_unico = f"{datetime.now().strftime('%Y%m%d%H%M')}_{arquivo_objeto.name}"
            caminho_fisico = os.path.join(TEMPLATES_DIR, nome_unico)
            caminho_final_banco = f"assets_global/templates/{nome_unico}"
            
            # Gravação física segura
            with open(caminho_fisico, "wb") as f:
                f.write(arquivo_objeto.getbuffer())

        if id_editando:
            # Lógica de Atualização (Edit)
            if arquivo_objeto:
                # Atualiza tudo, incluindo o novo arquivo
                sql = """UPDATE arquivos_templates 
                        SET nome_formulario=%s, template=%s, nome_arquivo_original=%s, 
                            caminho_arquivo=%s, tipo_arquivo=%s, data_upload=NOW()
                        WHERE id=%s"""
                cursor.execute(sql, (nome_form, trimestre, arquivo_objeto.name, 
                                     caminho_final_banco, arquivo_objeto.type, id_editando))
            else:
                # Atualiza apenas os textos, mantém o arquivo antigo
                sql = "UPDATE arquivos_templates SET nome_formulario=%s, template=%s WHERE id=%s"
                cursor.execute(sql, (nome_form, trimestre, id_editando))
        else:
            # Lógica de Novo Cadastro (Insert)
            if not arquivo_objeto: return False
            sql = """INSERT INTO arquivos_templates 
                    (nome_formulario, template, nome_arquivo_original, caminho_arquivo, tipo_arquivo, status, data_upload) 
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())"""
            cursor.execute(sql, (nome_form, trimestre, arquivo_objeto.name, 
                                 caminho_final_banco, arquivo_objeto.type, "ativo"))
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro no banco ao salvar template: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def listar_templates_db():
    """Retorna um DataFrame com todos os templates para exibição em tabelas."""
    conn = conectar()
    if not conn:
        return pd.DataFrame()
    try:
        # Usamos o engine do SQLAlchemy (definido no arquivo principal) ou a conexão direta
        query = """
            SELECT id, nome_formulario, template as trimestre, nome_arquivo_original, caminho_arquivo, status 
            FROM arquivos_templates 
            ORDER BY template ASC, id DESC
        """
        # Nota: pd.read_sql funciona bem com a conexão do mysql-connector
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Erro ao listar templates: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

# ==========================================================
# 7. CONHECIMENTO DA IA
# ==========================================================
def buscar_conhecimento_ia(termo_busca):
    """Busca trechos de conhecimento para alimentar o contexto da IA."""
    conn = conectar()
    if not conn: return ""
    cursor = None 
    try:
        cursor = conn.cursor(dictionary=True)
        # Limpa o termo e prepara para busca parcial
        termo = f"%{termo_busca.strip()}%"
        
        # Buscamos os 3 trechos mais relevantes que estejam ativos
        query = """
            SELECT conteudo FROM ia_conhecimento 
            WHERE status = 'ativo' AND (conteudo LIKE %s OR nome LIKE %s) 
            LIMIT 3
        """
        cursor.execute(query, (termo, termo))
        resultados = cursor.fetchall()       
        
        if not resultados: 
            return ""
            
        # Une os textos com um separador claro para a IA entender que são fontes diferentes
        contexto = "\n---\n".join([r['conteudo'] for r in resultados if r['conteudo']])
        return contexto
    except Exception as e:
        print(f"❌ Erro ao buscar conhecimento: {e}")
        return ""
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def registrar_no_banco(nome, tipo, caminho, descricao, texto_extraido):
    """Registra novos textos ou documentos na base de conhecimento da IA."""
    conn = conectar()
    if not conn: return False
    cursor = None
    try:
        cursor = conn.cursor()
        # Garante que o texto extraído não seja nulo e remove espaços desnecessários
        texto_limpo = texto_extraido.strip() if texto_extraido else ""
        
        sql = """INSERT INTO ia_conhecimento 
                 (nome, tipo_conteudo, caminho_ou_url, conteudo, descricao, status) 
                 VALUES (%s, %s, %s, %s, %s, 'ativo')"""
        
        cursor.execute(sql, (nome, tipo, caminho, texto_limpo, descricao))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar conhecimento no banco: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def consultar_base_ativa():
    """Retorna todos os materiais de conhecimento para a tabela do Admin."""
    conn = conectar()
    if not conn:
        return pd.DataFrame()
    try:
        # Buscamos metadados (sem o campo 'conteudo' que é pesado) para a tabela de gestão
        query = """
            SELECT id, nome, tipo_conteudo, caminho_ou_url, descricao, data_subida 
            FROM ia_conhecimento 
            ORDER BY id DESC
        """
        df = pd.read_sql(query, conn)
        return df
    except Exception as e:
        st.error(f"Erro ao listar base de conhecimento: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def deletar_material_db(id_db):
    """Remove um material da base de conhecimento."""
    conn = conectar()
    if not conn: return False
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ia_conhecimento WHERE id = %s", (id_db,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Erro ao deletar material: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()