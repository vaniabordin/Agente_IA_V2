import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

st.title("🔍 Scanner de Compatibilidade Gemini")

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ GEMINI_API_KEY não encontrada.")
else:
    genai.configure(api_key=api_key)
    
    try:
        st.write("### 1. Modelos Disponíveis na sua Chave:")
        # Lista todos os modelos que sua API Key pode acessar
        modelos_disponiveis = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                modelos_disponiveis.append(m.name)
                st.code(m.name)

        st.divider()
        
        st.write("### 2. Teste de Resposta Longa (Sem Cortes)")
        versao_para_teste = st.selectbox("Selecione um modelo da lista acima:", modelos_disponiveis)
        
        if st.button(f"Testar Estresse no {versao_para_teste}"):
            model = genai.GenerativeModel(versao_para_teste)
            with st.spinner("Gerando texto longo..."):
                # Pedimos um texto gigante para forçar o limite
                prompt = "Escreva um guia completo e exaustivo sobre empreendedorismo, com 5 parágrafos longos."
                
                response = model.generate_content(
                    prompt,
                    generation_config={"max_output_tokens": 2048} # Aumentamos o limite de saída
                )
                
                st.info(f"Tamanho da resposta: {len(response.text)} caracteres.")
                st.write(response.text)
                
                if response.text.endswith(('.', '!', '?')):
                    st.success("✅ Finalizou corretamente!")
                else:
                    st.error("❌ Frase cortada detectada.")

    except Exception as e:
        st.error(f"Erro ao listar modelos: {e}")