import os
import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import tempfile

# ==========================================================
# 1. CONFIGURAÇÃO GLOBAL (USANDO ST.SECRETS)
# ==========================================================
try:     
    API_KEY_GEMINI = st.secrets.get("GEMINI_API_KEY")
    if API_KEY_GEMINI:
        genai.configure(api_key=API_KEY_GEMINI)
    else:
        st.error("Chave GEMINI_API_KEY não configurada.")
except Exception as e:
    st.error(f"Erro ao configurar API: {e}")

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
        model = genai.GenerativeModel('gemini-2.5-flash')
        conteudo_extraido = ""
        caminho_final_banco = None

        # --- FLUXO ARQUIVO (UploadedFile do Streamlit ou Path) ---
        if hasattr(origem_conteudo, 'name') or (isinstance(origem_conteudo, str) and os.path.exists(origem_conteudo)):
            
            # Se for um upload do Streamlit, precisamos salvar fisicamente para o Gemini ler
            if hasattr(origem_conteudo, 'read'):
                temp_dir = tempfile.gettempdir()                
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                
                caminho_temp = os.path.join(temp_dir, origem_conteudo.name)
                with open(caminho_temp, "wb") as f:
                    f.write(origem_conteudo.getbuffer())
                
                caminho_final_banco = caminho_temp
                arquivo_para_processar = caminho_temp
            else:
                arquivo_para_processar = origem_conteudo
                caminho_final_banco = origem_conteudo

            nome_arquivo = nome_para_db if nome_para_db else os.path.basename(arquivo_para_processar)
            
            # Upload para o Google Gemini
            documento = genai.upload_file(path=arquivo_para_processar)
            
            prompt = (
                f"Extraia todo o conteúdo textual do arquivo {nome_arquivo}. "
                "Retorne apenas o texto puro do documento para ser usado como base de conhecimento "
                "de uma IA acadêmica. Mantenha a fidelidade aos dados."
            )
            
            response = model.generate_content([prompt, documento])
            conteudo_extraido = response.text
            
            # Deleta o arquivo do servidor do Google
            documento.delete()

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
                # Fallback: Caso não haja legenda, tenta análise visual (se disponível no modelo)
                prompt_fallback = (
                    f"Analise o vídeo no link {origem_conteudo}. "
                    "Descreva detalhadamente todos os pontos ensinados para criar uma base de conhecimento."
                )
                response = model.generate_content(prompt_fallback)
                conteudo_extraido = response.text
            
        else:
            return False, "Origem de conteúdo não suportada.", None

        return True, conteudo_extraido, caminho_final_banco

    except Exception as e:
        return False, f"Erro no processamento da IA: {str(e)}", None