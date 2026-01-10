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
    client_meta = OpenAI(
        base_url="https://api.groq.com/openai/v1", 
        api_key=st.secrets["META_AI_API_KEY"]
    )
except Exception:
    st.error("Chave META_AI_API_KEY ausente.")
    
# Modelo atualizado conforme teste de sucesso
MODELO_DOCS = 'models/gemini-2.5-flash' 
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
                            "Sua missão é impulsionar o usuário com uma energia contagiante, lúdica e objetiva, sem perder o foco. "
                            "DIRETRIZES: 1. Use metáforas de foguetes, ignição ou órbita. "
                            "2. Seja motivador: use exclamações e incentive a ação. "
                            "3. Seja direto: responda em no máximo 2 frases curtas, unindo o conceito ao lúdico."
                            f"Base de Conhecimento: {conhecimento}"
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
    """Análise técnica de arquivos usando Gemini - Flash"""
    try:
        # 1. Definição do Prompt
        prompt_instrucao = f"""
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
        model = genai.GenerativeModel(MODELO_DOCS)
        
        if upload_arquivo.name.endswith('.xlsx'):
            df = pd.read_excel(upload_arquivo)
            conteudo_texto = df.to_csv(index=False)
            # Envio de texto para Excel (mais estável)
            response = model.generate_content([prompt_instrucao, f"Conteúdo Excel: {conteudo_texto}"])
        else:
            # Envio de binários (PDF/Imagens)
            documento = {
                "mime_type": upload_arquivo.type,
                "data": upload_arquivo.getvalue()
            }
            response = model.generate_content([prompt_instrucao, documento])

        # Limpeza robusta do JSON
        texto_limpo = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpo)

    except Exception as e:
        registrar_erro_ia(st.session_state.get("usuario_id"), nome_etapa, "Gemini_Analise", str(e))
        return {
            "porcentagem": 0, 
            "zona": "Erro", 
            "cor": "#FF4B4B", 
            "feedback_ludico": f"Erro na análise: {str(e)}",
            "perguntas_faltantes": [],
            "dicas": "Verifique se o arquivo não está corrompido ou protegido por senha."
        }