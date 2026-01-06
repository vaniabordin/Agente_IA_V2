import streamlit as st
import pandas as pd
import json
import os
from utils.db import conectar
from utils.ui import criar_grafico_circular

def aba_consulta_respostas():
    # ÚNICO CABEÇALHO DA PÁGINA
    st.header("🔍 Resultados das Startups")
    
    conn = conectar()
    if not conn:
        st.error("Erro ao conectar ao banco de dados.")
        return

    try:
        cursor = conn.cursor(dictionary=True)
       
        # --- 1. SELEÇÃO INDIVIDUAL DO ALUNO ---
        cursor.execute("SELECT id, username FROM usuarios WHERE role = 'aluno'")
        alunos = cursor.fetchall()
        
        if not alunos:
            st.warning("Nenhum aluno cadastrado no sistema.")
            return

        lista_alunos = {a['username']: a['id'] for a in alunos}
        
        # Filtro de seleção direto
        nome_aluno = st.selectbox("Selecione a Startup/Aluno para detalhes:", options=list(lista_alunos.keys()))
        aluno_id = lista_alunos[nome_aluno]

        # --- 2. BUSCA O HISTÓRICO INDIVIDUAL ---
        query = """
            SELECT id, etapa, caminho_arquivo_aluno, nome_arquivo_original, 
                   porcentagem, zona, feedback_ludico, perguntas_faltantes, dicas, data_avaliacao 
            FROM avaliacoes_ia  
            WHERE usuario_id = %s 
            ORDER BY data_avaliacao DESC
        """
        cursor.execute(query, (aluno_id,))
        entregas = cursor.fetchall()

        if not entregas:
            st.info(f"O aluno **{nome_aluno}** ainda não realizou nenhuma entrega.")
        else:
            # Exibe cada entrega em um expander
            for entrega in entregas:
                data_dt = entrega['data_avaliacao']
                data_formatada = data_dt.strftime("%d/%m/%Y %H:%M") if data_dt else "Data N/A"
                
                with st.expander(f"📅 {entrega['etapa']} - Avaliado em: {data_formatada}"):
                    # Conteúdo interno (Download e Diagnóstico)
                    st.markdown("### 📥 Arquivo Enviado")
                    caminho = entrega['caminho_arquivo_aluno']
                    if caminho and os.path.exists(caminho):
                        with open(caminho, "rb") as f:
                            st.download_button(
                                label=f"Baixar {entrega['nome_arquivo_original']}",
                                data=f,
                                file_name=entrega['nome_arquivo_original'] or "planilha.xlsx",
                                key=f"dl_admin_{entrega['id']}"
                            )
                    
                    st.divider()
                    st.markdown("### 🤖 Diagnóstico da IA")
                    
                    # Gráfico e Métricas
                    porcentagem = entrega.get('porcentagem', 0)
                    c_esq, c_meio, c_dir = st.columns([1, 2, 1])
                    with c_meio:
                        st.plotly_chart(criar_grafico_circular(porcentagem), use_container_width=True)
                    
                    st.write(f"**Performance:** `{porcentagem}%` | **Zona:** `{entrega['zona']}`")
                    st.info(f"**Parecer:** {entrega['feedback_ludico']}")
                    
                    if entrega.get('perguntas_faltantes'):
                        try:
                            faltantes = json.loads(entrega['perguntas_faltantes']) if isinstance(entrega['perguntas_faltantes'], str) else entrega['perguntas_faltantes']
                            if faltantes:
                                with st.expander("⚠️ Itens não detectados"):
                                    for item in faltantes:
                                        st.write(f"• {item}")
                        except: pass

    except Exception as e:
        st.error(f"Erro: {str(e)}")
    finally:
        conn.close()