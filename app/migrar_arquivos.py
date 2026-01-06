import os
import mysql.connector
from dotenv import load_dotenv
import PyPDF2

load_dotenv()

# 1. Configuração das Pastas de Arquivos
PASTAS_CONHECIMENTO = {
    "Q1": "app/data/aulas_q1",
    "Q2": "app/data/aulas_q2"
}

# 2. Configuração dos Links (Separados por Trimestre)
LINKS_POR_PERIODO = {    
    "Q2": {
        "Calendário e Criativos: organizando sua produção de conteúdo": "https://www.youtube.com/watch?v=Yg8zBevhPH0&list=PLBsSLfexwuRjKuSZXFJDZ31Yxz4hRyQVa&index=6",
        "Planejamento de Mídia: escolhendo canais e orçamento": "https://www.youtube.com/watch?v=dp9RqlPT-VY&list=PLBsSLfexwuRjKuSZXFJDZ31Yxz4hRyQVa&index=5",
        "Landing Pages que Convertem: copy e estrutura": "https://www.youtube.com/watch?v=rNPZjYgWgAM&list=PLBsSLfexwuRjKuSZXFJDZ31Yxz4hRyQVa&index=4",
        "Gatilhos de Conversão e Jornada Pós-Lead": "https://www.youtube.com/watch?v=oCCFCppgzo4&list=PLBsSLfexwuRjKuSZXFJDZ31Yxz4hRyQVa&index=2",
        "CRM e Automação: primeiros passos": "https://www.youtube.com/watch?v=Vd78qJw3E3s&list=PLBsSLfexwuRjKuSZXFJDZ31Yxz4hRyQVa&index=3",
        "SETUP TÉCNICO: Rastreio, Pixels e Integrações": "https://www.youtube.com/watch?v=yZfNlPMDNIk&list=PLBsSLfexwuRjKuSZXFJDZ31Yxz4hRyQVa&index=1"
    }
}

def extrair_texto_pdf(caminho_pdf):
    try:
        with open(caminho_pdf, "rb") as f:
            leitor = PyPDF2.PdfReader(f)
            texto = ""
            for pagina in leitor.pages:
                resumo = pagina.extract_text()
                if resumo: texto += resumo
            return texto
    except Exception as e:
        print(f"❌ Erro ao ler PDF {caminho_pdf}: {e}")
        return ""

def migrar():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
    cursor = conn.cursor()
    # Limpa a base de conhecimento antes de re-alimentar (CUIDADO: remove registros manuais)
    cursor.execute("DELETE FROM ia_conhecimento")

    # --- PARTE 1: MIGRANDO ARQUIVOS (PDF/TXT) ---
    for periodo, caminho_pasta in PASTAS_CONHECIMENTO.items():
        if os.path.exists(caminho_pasta):
            arquivos = [f for f in os.listdir(caminho_pasta) if f.endswith(('.pdf', '.txt'))]
            print(f"📂 [Arquivos] Processando {len(arquivos)} itens do {periodo}...")

            for nome_arq in arquivos:
                caminho_completo = os.path.join(caminho_pasta, nome_arq)
                
                if nome_arq.endswith('.pdf'):
                    conteudo = extrair_texto_pdf(caminho_completo)
                else:
                    with open(caminho_completo, 'r', encoding='utf-8') as f:
                        conteudo = f.read()

                # Adiciona etiqueta no conteúdo para a IA filtrar
                descricao_final = f"[{periodo}] CONTEÚDO DO ARQUIVO: {conteudo}"
                
                sql = "INSERT INTO ia_conhecimento (nome, tipo_conteudo, caminho_ou_url, descricao) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (nome_arq, 'arquivo', caminho_completo, descricao_final))
                print(f"✅ {periodo} - Arquivo: {nome_arq}")

    # --- PARTE 2: MIGRANDO LINKS (DIFERENCIADOS POR Q1/Q2) ---
    for periodo, links in LINKS_POR_PERIODO.items():
        print(f"🔗 [Links] Processando {len(links)} links do {periodo}...")
        for nome, url in links.items():
            # Adiciona a etiqueta também na descrição do link
            descricao_link = f"[{periodo}] Link de aula/referência externa sobre {nome}"
            
            sql = "INSERT INTO ia_conhecimento (nome, tipo_conteudo, caminho_ou_url, descricao) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (nome, 'youtube' if 'youtube' in url else 'link', url, descricao_link))
            print(f"✅ {periodo} - Link: {nome}")

    conn.commit()
    cursor.close()
    conn.close()
    print("\n✨ Migração concluída com sucesso e trimestres diferenciados!")

if __name__ == "__main__":
    migrar()