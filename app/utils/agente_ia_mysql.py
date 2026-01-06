import os
import google.generativeai as genai
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import re

load_dotenv()

# Configuração da API
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

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

def processar_conteudo_ia(caminho_ou_url, nome_para_db=None):
    """
    Função para extrair conhecimento de PDFs ou Vídeos do YouTube.
    Retorna (Sucesso: bool, Conteudo_ou_Erro: str)
    """
    try:
        # Modelo Gemini 2.5 Flash
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        conteudo_extraido = ""

        # --- FLUXO ARQUIVO LOCAL (PDF) ---
        if os.path.exists(caminho_ou_url):
            nome_arquivo = nome_para_db if nome_para_db else os.path.basename(caminho_ou_url)
            
            # Upload para o Google Gemini
            documento = genai.upload_file(path=caminho_ou_url)
            
            prompt = (
                f"Extraia todo o conteúdo textual do arquivo {nome_arquivo}. "
                "Retorne apenas o texto puro do documento para ser usado como base de conhecimento "
                "de uma IA acadêmica. Mantenha a fidelidade aos dados."
            )
            
            response = model.generate_content([prompt, documento])
            conteudo_extraido = response.text
            
            # Deleta o arquivo temporário do servidor do Google
            documento.delete()

        # --- FLUXO YOUTUBE (Com Transcrição) ---
        elif "youtube.com" in caminho_ou_url or "youtu.be" in caminho_ou_url:
            video_id = extrair_id_youtube(caminho_ou_url)
            
            if not video_id:
                return False, "Não foi possível identificar o ID do vídeo do YouTube."

            try:
                # Tenta buscar a legenda original (Português ou Inglês)
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'en'])
                texto_transcrito = " ".join([t['text'] for t in transcript_list])

                # Envia a transcrição para a IA organizar
                prompt = (
                    "Abaixo está a transcrição bruta de um vídeo. "
                    "Sua tarefa é organizar este texto em um material de estudo estruturado e detalhado. "
                    "Não resuma; garanta que todas as diretrizes e ensinamentos técnicos sejam preservados.\n\n"
                    f"TRANSCRIÇÃO:\n{texto_transcrito}"
                )
                response = model.generate_content(prompt)
                conteudo_extraido = response.text

            except Exception as e:
                # Caso o vídeo não tenha legenda, usa a capacidade visual do Gemini (Fallback)
                prompt_fallback = (
                    f"Analise o vídeo no link {caminho_ou_url}. "
                    "Assista ao conteúdo e descreva detalhadamente todos os pontos ensinados, "
                    "criando uma base de conhecimento completa para um aluno."
                )
                response = model.generate_content(prompt_fallback)
                conteudo_extraido = response.text
            
        else:
            return False, "Caminho de arquivo ou URL inválida."

        return True, conteudo_extraido

    except Exception as e:
        return False, f"Erro no processamento da IA: {str(e)}"