import streamlit as st
import os
import time
import json
import plotly.graph_objects as go
import pandas as pd
from utils.db import (
    conectar, verificar_etapa_concluida, salvar_conclusao_etapa, 
    salvar_entrega_e_feedback, buscar_ultimo_feedback_ia
)
from utils.ia_chat import analisar_documento_ia
from utils.ui import aplicar_estilo_fcj
from utils.menu import renderizar_menu
from utils.ui import criar_grafico_circular

# --- CONFIGURAÇÃO E SEGURANÇA --- #
if st.session_state.get("usuario_id") is None:
    st.switch_page("Home.py") 
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA --- #
st.set_page_config(
    page_title="Template Q1 - FCJ",
    layout="wide"
)

# CSS para interface limpa e institucional
st.markdown("""
    <style>
        [data-testid="stHeaderNav"] {display: none !important;}
        [data-testid="stSidebarNav"] {display: none !important;}
        .block-container {padding-top: 1.5rem;}
        .stExpander {border: 1px solid #dee2e6; border-radius: 10px; margin-bottom: 1rem;}
    </style>
""", unsafe_allow_html=True)

aplicar_estilo_fcj()
renderizar_menu()

# --- PÁGINA PRINCIPAL --- #
def Q1_page():
    st.title("Q1 - Fundação: Diagnóstico Estratégico e Posicionamento")
    
    user_id = st.session_state.get("usuario_id")
    conn = conectar()
    if not conn: return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome_formulario, caminho_arquivo, nome_arquivo_original 
            FROM arquivos_templates 
            WHERE template = 'Q1' AND status = 'ativo' 
            ORDER BY id ASC
        """)
        templates = cursor.fetchall()

        if not templates:
            st.info("Nenhum formulário Q1 disponível no momento.")
            return

        # --- 1. BARRA DE PROGRESSO (RESERVA DE ESPAÇO) ---
        container_progresso = st.empty()
        st.divider()
        
        # --- 2. LOOP DE ETAPAS ---
        etapa_liberada = True 
        lista_final_status = [] 

        for idx, temp in enumerate(templates):
            t_id = temp['id']
            nome_etapa = temp['nome_formulario']

            concluida = verificar_etapa_concluida(user_id, nome_etapa)
            lista_final_status.append(concluida)
            
            # Cache de Feedback
            if f"feedback_{t_id}" not in st.session_state:
                feedback_salvo = buscar_ultimo_feedback_ia(user_id, nome_etapa)
                if feedback_salvo:
                    st.session_state[f"feedback_{t_id}"] = feedback_salvo
            
            label_expander = f"✅ {nome_etapa}" if concluida else f"📋 {nome_etapa}"
            
            with st.expander(label_expander, expanded=not concluida):
                col_tit, col_stat = st.columns([2, 1])
                
                with col_tit:
                    st.markdown(f"### {nome_etapa}")
                                
                with col_stat:
                    escolha = st.radio(
                        "Status da Etapa:", ["Em andamento", "Concluído"],
                        index=1 if concluida else 0,
                        key=f"rad_{t_id}",
                        horizontal=True,
                        disabled=not etapa_liberada
                    )
                    
                    if escolha == "Concluído" and not concluida:
                        if salvar_conclusao_etapa(user_id, nome_etapa):
                            st.rerun()

                if not etapa_liberada:
                    st.warning("🔒 Conclua a etapa anterior para liberar esta.")
                else:
                    # --- DOWNLOAD ---
                    st.markdown("#### 1. Preparação")
                    if temp['caminho_arquivo'] and os.path.exists(temp['caminho_arquivo']):
                        with open(temp['caminho_arquivo'], "rb") as f:
                            st.download_button(
                                label="⬇️ Baixar Template Modelo",
                                data=f,
                                file_name=temp['nome_arquivo_original'],
                                key=f"dl_{t_id}",
                                use_container_width=True
                            )
                    
                    # --- UPLOAD E ANÁLISE ---
                    st.write("") 
                    st.markdown("#### 2. Entrega e Validação")
                    upload_arquivo = st.file_uploader("Submeta seu arquivo (Excel, PDF ou Word)", type=['xlsx', 'pdf', 'docx'], key=f"up_{t_id}")

                    if upload_arquivo:
                        _, col_btn, _ = st.columns([1, 1, 1])
                        with col_btn:
                            if st.button(f"🤖 Analisar Documento", key=f"btn_ia_{t_id}", type="primary", use_container_width=True):
                                with st.spinner("O Agente IA está revisando..."):
                                    resultado = analisar_documento_ia(upload_arquivo, nome_etapa)
                                    
                                    if resultado.get('porcentagem', 0) > 0:
                                        if salvar_entrega_e_feedback(user_id, nome_etapa, upload_arquivo, resultado):
                                            salvar_conclusao_etapa(user_id, nome_etapa)
                                            st.toast("Análise finalizada com sucesso!")
                                            st.rerun()
                                    else:
                                        st.error(f"Não foi possível validar: {resultado.get('feedback_ludico')}")

                    # --- EXIBIÇÃO DE RESULTADOS IA ---
                    if f"feedback_{t_id}" in st.session_state:
                        res = st.session_state[f"feedback_{t_id}"]
                        st.divider()
                        
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.plotly_chart(criar_grafico_circular(res['porcentagem']), use_container_width=True, config={'displayModeBar': False})
                        with c2:
                            st.markdown(f"#### Diagnóstico de Maturidade")
                            st.markdown(f"**Nível:** <span style='color:{res['cor']}; font-size:1.2rem; font-weight:bold;'>{res['zona']}</span>", unsafe_allow_html=True)
                            st.markdown(f"""
                                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid {res['cor']};">
                                    <small style="text-transform: uppercase; font-weight: bold; color: {res['cor']};">Parecer do Mentor:</small><br>
                                    <span style="color: #113140; font-style: italic;">"{res['feedback_ludico']}"</span>
                                </div>
                            """, unsafe_allow_html=True)

                        # Exibição de Itens Faltantes e Dicas (Novos Campos)
                        if res.get('perguntas_faltantes'):
                            with st.expander("⚠️ Itens que a Ia não detectados como preenchidos:", expanded=False):
                                for item in res['perguntas_faltantes']:
                                    st.write(f"• {item}")

                        if res.get('dicas'):
                            st.info(f"💡 **Dica Estratégica:** {res['dicas']}")

            # Regra de negócio: A próxima só libera se a atual estiver concluída
            etapa_liberada = concluida 

        # --- 3. RENDERIZAÇÃO FINAL DA BARRA DE PROGRESSO ---
        total = len(templates)
        concluidas = sum(lista_final_status)
        valor_progresso = concluidas / total

        with container_progresso.container():
            col_p1, col_p2 = st.columns([4, 1])
            with col_p1:
                st.write(f"**Progresso no Q1:** {concluidas} de {total} etapas")
                st.progress(valor_progresso)
            with col_p2:
                if valor_progresso == 1.0:
                    st.button("Próximo Trimestre 🚀", on_click=lambda: st.switch_page("pages/Trimestre Q2.py"))

    finally:
        conn.close()

if __name__ == "__main__":
    Q1_page()