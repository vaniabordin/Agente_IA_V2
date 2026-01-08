import os
import json
import re
import streamlit as st
import mysql.connector
from mysql.connector import Error
import google.genai as genai
from google.genai.types import HarmCategory, HarmBlockThreshold, SafetySetting

# ==========================================================
# 1. CONFIGURAÇÃO GLOBAL (ST.SECRETS)
# ==========================================================

# Configuração de Banco de Dados vinda do secrets.toml
# O Streamlit lê o bloco [mysql] como um dicionário
try:
    DB_CONFIG = {
        'host': st.secrets["mysql"]["host"],
        'port': st.secrets["mysql"]["port"],
        'user': st.secrets["mysql"]["user"],
        'password': st.secrets["mysql"]["password"],
        'database': st.secrets["mysql"]["database"],
        'ssl_verify_cert': True  # Importante para TiDB Cloud
    }
except Exception as e:
    st.error(f"Erro ao carregar configurações de banco: {e}")

CLIENT = None
MODEL_NAME_GLOBAL = "gemini-2.0-flash"

def configurar_gemini():
    global CLIENT
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada nos secrets")
        CLIENT = genai.Client(api_key=api_key)
        return CLIENT
    except Exception as e:
        st.error(f"Erro na API Gemini: {e}")
        return None

# ============================================================
# FUNÇÕES DE BANCO DE DADOS
# ============================================================

def salvar_avaliacao_mysql(usuario_id, etapa, nome_arquivo, porcentagem, feedback, zona="Parcial", cor="#FFCC00", perguntas_faltantes="", dicas=""):
    """
    Insere os resultados na tabela avaliacoes_ia conforme a nova estrutura.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = ("""
            INSERT INTO avaliacoes_ia 
            (usuario_id, etapa, nome_arquivo_original, porcentagem, zona, feedbackludico, cor, perguntas_faltantes, dicas, data_avaliacao) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """)
        
        valores = (
            usuario_id, 
            etapa, 
            nome_arquivo, 
            porcentagem, 
            zona, 
            feedback, 
            cor, 
            perguntas_faltantes, 
            dicas
        )
        
        cursor.execute(query, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        st.error(f"[ERRO MySQL] Falha ao salvar avaliação: {e}")
        return False

# ============================================================
# PROCESSAMENTO DE CONTEÚDO (ARQUIVOS E URLS)
# ============================================================

def processar_conteudo_ia(usuario_id, caminho_ou_url, nome_para_db=None):
    """Função principal para processar arquivos do aluno e salvar no DB."""
    global CLIENT
    if not CLIENT: configurar_gemini()
    
    nome_arquivo = nome_para_db if nome_para_db else os.path.basename(caminho_ou_url)
    file_id = None
    
    try:
        # Se for um arquivo local para upload
        if os.path.exists(caminho_ou_url):
            uploaded_file = CLIENT.files.upload(path=caminho_ou_url)
            file_id = uploaded_file.name
            prompt = f"Analise o arquivo {nome_arquivo}. Dê uma PONTUACAO: (1-100) e SUGESTÕES lúdicas de melhoria."
            contents = [prompt, uploaded_file]
        else:
            # Se for uma URL (Youtube ou Link)
            prompt = f"Analise o conteúdo em {caminho_ou_url}. Dê uma PONTUACAO: (1-100) e SUGESTÕES lúdicas."
            contents = [prompt, caminho_ou_url]

        response = CLIENT.models.generate_content(
            model=MODEL_NAME_GLOBAL,
            contents=contents
        )

        res_text = response.text
        # Parsing Simples de Pontuação
        pontuacao = 0
        match = re.search(r"PONTUACAO:\s*(\d+)", res_text)
        if match:
            pontuacao = int(match.group(1))
        
        # Salva no Banco de Dados com o usuario_id do aluno
        salvar_avaliacao_mysql(usuario_id, nome_arquivo, file_id, pontuacao, res_text)
        
        return True, res_text

    except Exception as e:
        return False, f"Erro no processamento: {str(e)}"

# ============================================================
# VALIDAÇÃO JSON (Q1/Q2 FORMULÁRIOS)
# ============================================================

def validar_etapa_generica(usuario_id, dados_etapa: dict, q_contexto="Q1"):
    """Analisa dados de dicionário e retorna JSON."""
    global CLIENT
    if not CLIENT: configurar_gemini()

    prompt = f"Avalie estes dados de {q_contexto} e retorne JSON com 'validations', 'suggestions' e 'summary'."
    
    try:
        response = CLIENT.models.generate_content(
            model=MODEL_NAME_GLOBAL,
            contents=[prompt, json.dumps(dados_etapa)],
            config={"response_mime_type": "application/json"}
        )
        
        resultado = json.loads(response.text)
        # Opcional: Salvar essa validação de formulário também no DB
        salvar_avaliacao_mysql(usuario_id, f"Formulário {q_contexto}", None, 100, response.text)
        
        return resultado
    except Exception as e:
        return {"summary": f"Erro: {str(e)}"}

# Atalhos
def validar_q1(user_id, dados): return validar_etapa_generica(user_id, dados, "Q1")