import streamlit as st
import google.generativeai as genai
import pandas as pd
from openai import OpenAI
import os
import json
import time
from utils.db import registrar_erro_ia, buscar_conhecimento_ia

# ==========================================================
# 1. CONFIGURAÇÃO GLOBAL (ST.SECRETS)
# ==========================================================
try:
    API_KEY_GEMINI = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY_GEMINI)
except Exception:
    st.error("Chave GEMINI_API_KEY ausente.")

try:
    # Cliente configurado para usar Meta AI (Llama 3 via Groq)
    client_meta = OpenAI(
        base_url="https://api.groq.com/openai/v1", 
        api_key=st.secrets["META_AI_API_KEY"]
    )
except Exception:
    st.error("Chave META_AI_API_KEY ausente.")
    
MODELO_DOCS = 'gemini-1.5-flash' 
MODELO_META = 'llama-3.3-70b-versatile'

# ==========================================================
# 2. MENTORIA SIDEBAR (USANDO META AI)
# ==========================================================
def mentoria_ia_sidebar():
    """Chat lateral utilizando estritamente a Meta AI"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Identifica o contexto da página atual (Q1, Q2, Q3 ou Q4)
    page_id = st.session_state.get("current_page", "Geral")
    mapa_temas = {
        "q1_page": "Diagnóstico e Fundação",
        "q2_page": "Tração e Vendas",
        "q3_page": "Escala e Processos",
        "q4_page": "Governança e Captação"
    }
    tema_atual = mapa_temas.get(page_id, "Aceleração de Startups")

    st.sidebar.divider()
    col_tit, col_btn = st.sidebar.columns([0.6, 0.4])
    
    with col_tit:
        st.sidebar.divider()
        st.sidebar.markdown(f"### 🤖 Mentor Meta AI")
    
    with col_btn:
        # Chave baseada na página para evitar conflitos de widgets
        key_limpar = f"btn_limpar_sidebar_{st.session_state.get('current_page', 'home')}"
        if st.sidebar.button("🗑️ Limpar Histórico", width="stretch", key=key_limpar):
            st.session_state.messages = []
            st.rerun()
            
        st.sidebar.write("")
    # Histórico de Chat
    chat_container = st.sidebar.container(height=400)
    for msg in st.session_state.messages:
        with chat_container.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input (Key estática para não perder o foco ao digitar)
    if prompt := st.sidebar.chat_input("Dúvida sobre esta etapa?", key=f"input_{page_id}"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)

        with chat_container.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            
            try:
                # 1. Busca Conhecimento (RAG)
                conhecimento = buscar_conhecimento_ia(prompt)
                
                # 2. Chamada Meta AI (Groq)
                response = client_meta.chat.completions.create(
                    model=MODELO_META,
                    messages=[
                        {"role": "system", "content": (
                            f"Você é o agente IA da FCJ. O usuário está na fase: {tema_atual}. "
                            "Sua personalidade é MOTIVADORA, LÚDICA e OBJETIVA. "
                            "Use metáforas de crescimento de startups (foguetes, tração, pista), mas vá direto ao ponto."
                            "Responda de forma extremamente concisa (máximo 2 frases curtas). " # Reforço da objetividade
                            f"Base de Conhecimento FCJ: {conhecimento}"
                        )},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        placeholder.markdown(full_response + "▌")
                
                placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                registrar_erro_ia(st.session_state.get("usuario_id"), "MetaAI_Sidebar", "Erro", str(e))
                placeholder.error("Mentor temporariamente offline.")

# ==========================================================
# 3. ANALISADOR DE DOCUMENTOS (USANDO GEMINI)
# ==========================================================
def analisar_documento_ia(upload_arquivo, nome_etapa):
    """Análise técnica de arquivos usando Gemini Vision/Flash"""
    try:
        model = genai.GenerativeModel(MODELO_DOCS)
        
        # Prompt focado em extração de dados e completude
        prompt = f"""
        Analise a completude do documento para a etapa: {nome_etapa}.
        Retorne APENAS um JSON:
        {{
            "porcentagem": (int de 0 a 100),
            "zona": "Incompleto/Parcial/Completo",
            "cor": "#hexadecimal",
            "feedback_ludico": "Frase de incentivo",
            "perguntas_faltantes": ["Campo 1", "Campo 2"],
            "dicas": "Sugestão técnica"
        }}
        """

        if upload_arquivo.name.endswith('.xlsx'):
            df = pd.read_excel(upload_arquivo)
            response = model.generate_content([prompt, f"Conteúdo do Excel:\n{df.to_string()}"])
        else:
            # Para PDF/DOCX usa a API de arquivos do Gemini
            user_id = st.session_state.get("usuario_id", "default")
            temp_name = f"temp_{user_id}_{upload_arquivo.name}"
            with open(temp_name, "wb") as f:
                f.write(upload_arquivo.getbuffer())
            
            uploaded_file = genai.upload_file(path=temp_name)
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(1)
                uploaded_file = genai.get_file(uploaded_file.name)
            
            response = model.generate_content([prompt, uploaded_file])
            uploaded_file.delete()
            os.remove(temp_name)

        # Limpeza do JSON
        raw_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(raw_text)

    except Exception as e:
        registrar_erro_ia(st.session_state.get("usuario_id"), "Gemini_Analise", "Erro", str(e))
        return {"porcentagem": 0, "zona": "Erro", "cor": "#FF4B4B", "feedback_ludico": "Falha ao processar arquivo."}