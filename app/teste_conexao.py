import os
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def testar_hibrido():
    print("--- Iniciando Diagnóstico do Agente IA FCJ ---")

    # 1. Teste Gemini (Análise de Documentos)
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model_gemini = genai.GenerativeModel('models/gemini-2.5-flash')
        res_gemini = model_gemini.generate_content("Oi", generation_config={"max_output_tokens": 10})
        print(f"✅ Gemini 2.5: Conectado! (Resposta: {res_gemini.text.strip()})")
    except Exception as e:
        print(f"❌ Gemini 2.5: Falhou. Erro: {e}")

    # 2. Teste Meta IA (Chat da Barra Lateral)
    try:
        client_meta = OpenAI(
            base_url="https://api.groq.com/openai/v1", 
            api_key=os.getenv("META_AI_API_KEY")
        )
        res_meta = client_meta.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Oi"}],
            max_tokens=10
        )
        print(f"✅ Meta IA (Llama): Conectado! (Resposta: {res_meta.choices[0].message.content.strip()})")
    except Exception as e:
        print(f"❌ Meta IA: Falhou. Verifique sua chave ou o base_url. Erro: {e}")

if __name__ == "__main__":
    testar_hibrido()