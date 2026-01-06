import streamlit as st
import google.generativeai as genai
import pandas as pd
from openai import OpenAI
import os
import json
import time
from utils.db import registrar_erro_ia, buscar_conhecimento_ia

# --- CONFIGURAÇÃO GLOBAL ---
API_KEY_GEMINI = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY_GEMINI)

client_meta = OpenAI(
    base_url="https://api.groq.com/openai/v1", 
    api_key=os.getenv("META_AI_API_KEY")
)

# Modelos confirmados para 2026
MODELO_DOCS = 'gemini-2.5-flash' 
MODELO_CHAT = 'llama-3.3-70b-versatile'


def mentoria_ia_sidebar():
    page_id = st.session_state.get("current_page", "default")
    
    st.markdown("""
        <style>
            [data-testid="stSidebar"] { min-width: 350px; }
            .stChatMessage { overflow-wrap: break-word; }
            .stChatMessage div, .stChatMessage p { 
                color: #FFFFFF !important;
                font-weight: 500 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.sidebar.divider()
    col_tit, col_btn = st.sidebar.columns([0.6, 0.4])
    with col_tit:
        st.markdown("### 🤖 Agente IA")
    with col_btn:
            # Geramos um ID único baseado no tempo para matar o erro de Duplicate Key
            timestamp_id = int(time.time() * 1000)
            unique_key = f"btn_limpar_{page_id}_{timestamp_id}"
            
            if st.button("Limpar", icon="🗑️", use_container_width=True, key=unique_key):
                st.session_state.messages = []
                st.rerun()
                
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    chat_container = st.sidebar.container()
   
    for message in st.session_state.messages:
        with chat_container.chat_message(message["role"]):
            st.markdown(message["content"])
    chat_key = f"chat_input_{page_id}_{int(time.time() * 1000)}"
    
    if prompt := st.sidebar.chat_input("Dúvida rápida?", key=chat_key):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)
    
        with chat_container.chat_message("assistant"):
            placeholder = st.empty()
            with st.spinner("Consultando base de conhecimento..."):   
                try:
                    conhecimento = buscar_conhecimento_ia(prompt)
                    if not conhecimento:
                        conhecimento = "Nenhum documento específico encontrado. Use seu conhecimento geral sobre a FCJ."
                    
                    response = client_meta.chat.completions.create(
                        model=MODELO_CHAT,
                        messages=[
                            {"role": "system", "content": (
                                "Você é o Mentor IA da FCJ. Sua personalidade é animada e focada em resultados. "
                                "Responda em no máximo 2 frases usando metáforas de negócios. "
                                f"[CONTEXTO]: {conhecimento}"
                            )},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    full_response = response.choices[0].message.content.strip()
                    for i in range(len(full_response)):
                        placeholder.markdown(full_response[:i+1] + "▌")
                        time.sleep(0.005)
                    placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    
                except Exception as e:
                    registrar_erro_ia(st.session_state.get("usuario_id"), "Chat_Meta", "Erro RAG", str(e))                    
                    placeholder.error("Erro ao processar consulta.")

def analisar_documento_ia(upload_arquivo, nome_etapa):
    """
    Analisa o documento enviado e retorna um dicionário com o diagnóstico.
    Importante: 'perguntas_faltantes' retorna como LISTA para exibição correta na UI.
    """
    temp_path = None
    try:
        model = genai.GenerativeModel(MODELO_DOCS)

        instrucao_analise = f"""
        Você é um mentor especialista da FCJ analisando a PERFORMANCE DE PREENCHIMENTO da etapa: {nome_etapa}.
        
        OBJETIVO:
        Avaliar o percentual de dados fornecidos no arquivo em relação ao template ideal.
        Não avalie a qualidade do negócio, apenas a completude do documento.

        REGRAS DE RETORNO:
        1. "porcentagem": Inteiro de 0 a 100 baseado no preenchimento dos campos.
        2. "feedback_ludico": Frase animada focada no progresso do preenchimento.
        3. "perguntas_faltantes": Liste apenas os 5 campos essenciais que ficaram vazios ou incompletos.
        4. "dicas": Até três dicas curtas sobre onde encontrar ou como calcular os dados faltantes.

        Responda APENAS em JSON:
        {{
            "porcentagem": (int),
            "zona": "Incompleto/Parcial/Completo",
            "cor": "#hex",
            "feedback_ludico": "string",
            "perguntas_faltantes": ["lista curta de strings"],
            "dicas": "string"
        }}
        """
        
        if upload_arquivo.name.endswith('.xlsx'):
            df = pd.read_excel(upload_arquivo)
            conteudo_texto = df.to_string()
            prompt_excel = f"{instrucao_analise}\n\nDados do Arquivo:\n{conteudo_texto}"
            response = model.generate_content(prompt_excel)
        else:
            user_id = st.session_state.get("usuario_id", "default")
            temp_path = f"temp_{user_id}_{int(time.time())}_{upload_arquivo.name}"
            with open(temp_path, "wb") as f:
                f.write(upload_arquivo.getbuffer())
            
            documento = genai.upload_file(path=temp_path, mime_type=upload_arquivo.type)
            while documento.state.name == "PROCESSING":
                time.sleep(2)
                documento = genai.get_file(documento.name)
            
            response = model.generate_content([instrucao_analise, documento])
            documento.delete()

        # Extração limpa do JSON
        content = response.text
        resultado = json.loads(content[content.find('{'):content.rfind('}')+1])
        
        # Garantir que perguntas_faltantes seja uma LISTA Python real para a interface
        if isinstance(resultado.get("perguntas_faltantes"), str):
            try:
                resultado["perguntas_faltantes"] = json.loads(resultado["perguntas_faltantes"])
            except:
                resultado["perguntas_faltantes"] = [resultado["perguntas_faltantes"]]
        
        resultado.setdefault("perguntas_faltantes", [])
        resultado.setdefault("dicas", "Continue preenchendo os dados para uma análise completa!")
        
        return resultado

    except Exception as e:
        registrar_erro_ia(st.session_state.get("usuario_id"), "AnaliseDoc", "Erro", str(e))
        return {
            "porcentagem": 0, "zona": "Erro", "cor": "#FF4B4B",
            "feedback_ludico": "Erro técnico na análise.",
            "perguntas_faltantes": [],
            "dicas": ""
        }
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)