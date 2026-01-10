import google.generativeai as genai
import os
# Use a NOVA CHAVE aqui
CHAVE = "AIza...."
# USE A CHAVE QUE VOCÊ ACABOU DE CRIAR NO NOVO PROJETO
try:
    print("🚀 Iniciando Teste de Resgate...")
    genai.configure(api_key=CHAVE)
    
    # Listar modelos disponíveis para sua chave (Isso tirará a prova real)
    print("Modelos disponíveis para você:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f" - {m.name}")

    # Tentar gerar conteúdo com o nome completo
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    response = model.generate_content("Diga: Agente pronto!")
    
    print("-" * 30)
    print(f"RESPOSTA: {response.text}")
    print("✅ SUCESSO TOTAL!")

except Exception as e:
    print(f"❌ ERRO: {e}")