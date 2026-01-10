import os
import streamlit as st
import google.generativeai as genai 
from youtube_transcript_api import YouTubeTranscriptApi
import re
import time

# ==========================================================
# 1. CONFIGURAÇÃO GLOBAL (USANDO ST.SECRETS)
# ==========================================================
try:     
    API_KEY_GEMINI = st.secrets.get("GEMINI_API_KEY")
    if API_KEY_GEMINI:        
        # Configuração para a biblioteca estável google-generativeai
        genai.configure(api_key=API_KEY_GEMINI)
    else:
        st.error("Chave GEMINI_API_KEY não configurada.")
except Exception as e:
    st.error(f"Erro ao configurar API: {e}")

# Modelo que funcionou nos seus testes de terminal
MODELO = 'models/gemini-2.5-flash'

def extrair_id_youtube(url):
    """
    Extrai o ID do vídeo de URLs comuns do YouTube.
    """
    padroes = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu.be\/([0-9A-Za-z_-]{11})"
    ]
    for padrao in padroes:
        match = re.search(padrao, url)
        if match:
            return match.group(1)
    return None

def processar_conteudo_ia(origem_conteudo, nome_para_db=None):
    """
    Função para extrair conhecimento de PDFs (UploadedFile) ou Vídeos do YouTube (URL).
    Retorna (Sucesso: bool, Conteudo_ou_Erro: str, Caminho_Salvo: str)
    """
    try:
        # Modelo Gemini          
        conteudo_extraido = ""
        caminho_final_banco = None
        
        # Inicializa o modelo conforme biblioteca estável
        model = genai.GenerativeModel(MODELO)

        # --- FLUXO ARQUIVO (UploadedFile do Streamlit ou Path) ---
        if hasattr(origem_conteudo, 'name') or (isinstance(origem_conteudo, str) and os.path.exists(origem_conteudo)):
            
            # Se for um upload do Streamlit, precisamos salvar fisicamente para o Gemini ler
            if hasattr(origem_conteudo, 'read'):
                diretorio_base = os.path.join(os.getcwd(), "knowledge_base")
                                
                if not os.path.exists(diretorio_base):
                    os.makedirs(diretorio_base)
                
                nome_limpo = os.path.basename(origem_conteudo.name)
                caminho_salvamento = os.path.join(diretorio_base, nome_limpo)
                
                with open(caminho_salvamento, "wb") as f:
                    f.write(origem_conteudo.getbuffer())
                
                caminho_final_banco = caminho_salvamento
                arquivo_para_processar = caminho_salvamento
                
            else:
                arquivo_para_processar = origem_conteudo
                caminho_final_banco = origem_conteudo
             
            # Upload para o Google Gemini usando a File API estável
            documento = genai.upload_file(path=arquivo_para_processar)
            
            # Aguarda o processamento do arquivo no servidor
            while documento.state.name == "PROCESSING":
                time.sleep(2)
                documento = genai.get_file(documento.name)

            if documento.state.name == "FAILED":
                raise Exception("Falha ao processar arquivo no servidor do Google.")
            
            prompt = (
                f"Extraia todo o conteúdo textual do documento. "
                "Retorne apenas o texto puro do documento para ser usado como base de conhecimento "
                "de uma IA acadêmica. Mantenha a fidelidade aos dados."
            )
                        
            # Chamada de geração corrigida para a biblioteca estável
            response = model.generate_content([prompt, documento])
            conteudo_extraido = response.text
            
            # Deleta o arquivo do servidor do Google para limpar cota
            genai.delete_file(documento.name)

        # --- FLUXO YOUTUBE (URL) ---
        elif isinstance(origem_conteudo, str) and ("youtube.com" in origem_conteudo or "youtu.be" in origem_conteudo):
            video_id = extrair_id_youtube(origem_conteudo)
            caminho_final_banco = origem_conteudo # No caso de vídeo, o "caminho" é a URL
            
            if not video_id:
                return False, "ID do YouTube inválido.", None

            try:
                # Tenta buscar a legenda original
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                texto_transcrito = " ".join([t['text'] for t in transcript_list])

                prompt = (
                    "Abaixo está a transcrição bruta de um vídeo. "
                    "Organize este texto em um material de estudo estruturado e detalhado. "
                    "Não resuma drasticamente; preserve os ensinamentos técnicos.\n\n"
                    f"TRANSCRIÇÃO:\n{texto_transcrito}"
                )

                response = model.generate_content(prompt)
                conteudo_extraido = response.text
                
            except Exception:
                # Fallback: Caso não haja legenda, tenta análise visual pelo prompt
                prompt_fallback = (
                    f"Analise o conteúdo do vídeo no link {origem_conteudo}. "
                    "Descreva detalhadamente todos os pontos ensinados para criar uma base de conhecimento."
                )
                
                response = model.generate_content(prompt_fallback)
                conteudo_extraido = response.text
             
        else:
            return False, "Origem de conteúdo não suportada.", None

        return True, conteudo_extraido, caminho_final_banco

    except Exception as e:
        return False, f"Erro no processamento da IA: {str(e)}", None