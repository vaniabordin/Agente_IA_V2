import streamlit as st
import os
import json
import plotly.graph_objects as go
from utils.db import (
    conectar, verificar_etapa_concluida, salvar_conclusao_etapa, 
    salvar_entrega_e_feedback, buscar_ultimo_feedback_ia
)
from utils.ia_chat import analisar_documento_ia, mentoria_ia_sidebar
from utils.ui import aplicar_estilo_fcj, criar_grafico_circular
from utils.menu import renderizar_menu

# --- 1. CONFIGURAÇÃO E SEGURANÇA --- #
st.set_page_config(
    page_title="Template Q4 - FCJ",
    layout="wide"
)

# Bloqueio de acesso se não estiver logado
if st.session_state.get("usuario_id") is None:
    st.switch_page("Home.py") 
    st.stop()

# DEFINIÇÃO DE ID DA PÁGINA (Fundamental para evitar o erro DuplicateElementKey)
st.session_state["current_page"] = "q4" 

# Estilização consistente
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
mentoria_ia_sidebar()

# --- 2. VALIDAÇÃO DE ACESSO (TRAVA Q3) --- #
def validar_acesso_q4(user_id):
    conn = conectar()
    if not conn: return False
    try:
        cursor = conn.cursor(dictionary=True)
        # O Q4 só abre se o Q3 estiver 100% concluído
        cursor.execute("SELECT nome_formulario FROM arquivos_templates WHERE template = 'Q3' AND status = 'ativo'")
        etapas_q3 = cursor.fetchall()
        for etapa in etapas_q3:
            if not verificar_etapa_concluida(user_id, etapa['nome_formulario']):
                return False
        return True
    except Exception:
        return False
    finally:
        conn.close()

if not validar_acesso_q4(st.session_state.get("usuario_id")):
    st.warning("⚠️ Acesso Bloqueado: Você precisa concluir 100% das etapas do Q3 antes de iniciar o Q4.")
    
    # Botão com chave única para o Q4
    if st.button("⬅️ Voltar para o Q3", key="btn_voltar_q3"):
        st.switch_page("pages/Trimestre Q3.py")
    
    st.stop()

# --- 3. PÁGINA PRINCIPAL Q4 --- #
def Q4_page():
    st.title("Q4 - Estratégia: Pitch, Captação e Governança")
    st.markdown("Foco: Preparação para captação de investimento, estruturação de conselho e liquidez.")
    
    user_id = st.session_state.get("usuario_id")
    conn = conectar()
    if not conn: return

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nome_formulario, caminho_arquivo, nome_arquivo_original 
            FROM arquivos_templates 
            WHERE template = 'Q4' AND status = 'ativo' 
            ORDER BY id ASC
        """)
        templates = cursor.fetchall()

        if not templates:
            st.info("Nenhum formulário Q4 disponível no momento.")
            return

        # Barra de progresso final no topo
        container_progresso = st.empty()
        st.divider()
        
        etapa_liberada = True 
        status_final = [] 

        for idx, temp in enumerate(templates):
            t_id = temp['id']
            nome_etapa = temp['nome_formulario']
            concluida = verificar_etapa_concluida(user_id, nome_etapa)
            status_final.append(concluida)
            
            # Cache de Feedback (Padronizado)
            if f"feedback_{t_id}" not in st.session_state:
                fb = buscar_ultimo_feedback_ia(user_id, nome_etapa)
                if fb: st.session_state[f"feedback_{t_id}"] = fb
            
            label = f"✅ {nome_etapa}" if concluida else f"📋 {nome_etapa}"
            
            with st.expander(label, expanded=not concluida):
                col_tit, col_stat = st.columns([2, 1])
                with col_tit:
                    st.markdown(f"### {nome_etapa}")
                
                with col_stat:
                    escolha = st.radio("Status da Etapa:", ["Em andamento", "Concluído"],
                                     index=1 if concluida else 0,
                                     key=f"rad_q4_{t_id}", horizontal=True,
                                     disabled=not etapa_liberada)
                    
                    if escolha == "Concluído" and not concluida:
                        if salvar_conclusao_etapa(user_id, nome_etapa):
                            st.rerun()

                if not etapa_liberada:
                    st.info("🔒 Etapa bloqueada. Siga a ordem cronológica da jornada.")
                else:
                    # 1. Download
                    st.markdown("#### 1. Documentação Estratégica")
                    if temp['caminho_arquivo'] and os.path.exists(temp['caminho_arquivo']):
                        with open(temp['caminho_arquivo'], "rb") as f:
                            st.download_button(
                                label="⬇️ Baixar Template de Governança", 
                                data=f, 
                                file_name=temp['nome_arquivo_original'],
                                key=f"dl_q4_{t_id}", 
                                use_container_width=True
                            )
                    
                    # 2. Upload e Auditoria IA
                    st.write("")
                    st.markdown("#### 2. Auditoria e Validação")
                    up = st.file_uploader("Submeta o arquivo final para auditoria", type=['xlsx', 'pdf', 'docx'], key=f"up_q4_{t_id}")

                    if up:
                        _, col_btn, _ = st.columns([1, 1, 1])
                        with col_btn:
                            if st.button("🤖 Iniciar Auditoria Digital", key=f"btn_ia_q4_{t_id}", type="primary", use_container_width=True):
                                with st.spinner("Realizando auditoria de governança..."):
                                    resultado = analisar_documento_ia(up, nome_etapa)
                                    if resultado.get('porcentagem', 0) > 0:
                                        if salvar_entrega_e_feedback(user_id, nome_etapa, up, resultado):
                                            salvar_conclusao_etapa(user_id, nome_etapa)
                                            st.toast("Auditoria concluída!")
                                            st.rerun()
                                    else:
                                        st.error(f"Não foi possível validar: {resultado.get('feedback_ludico')}")

                    # 3. Resultado da Auditoria IA
                    if f"feedback_{t_id}" in st.session_state:
                        res = st.session_state[f"feedback_{t_id}"]
                        st.divider()
                        
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            st.plotly_chart(criar_grafico_circular(res['porcentagem']), use_container_width=True, config={'displayModeBar': False})
                        with c2:
                            st.markdown(f"#### Diagnóstico de Maturidade Final")
                            st.markdown(f"**Nível:** <span style='color:{res['cor']}; font-size:1.2rem; font-weight:bold;'>{res['zona']}</span>", unsafe_allow_html=True)
                            st.markdown(f"""
                                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid {res['cor']};">
                                    <small style="text-transform: uppercase; font-weight: bold; color: {res['cor']};">Parecer do Auditor:</small><br>
                                    <span style="color: #113140; font-style: italic;">"{res['feedback_ludico']}"</span>
                                </div>
                            """, unsafe_allow_html=True)

                        # Itens Faltantes com proteção contra erros de formatação
                        if res.get('perguntas_faltantes'):
                            with st.expander("⚠️ Pontos de atenção detectados pela auditoria:", expanded=False):
                                faltantes = res['perguntas_faltantes']
                                if isinstance(faltantes, str):
                                    try:
                                        faltantes = json.loads(faltantes.replace("'", '"'))
                                    except:
                                        faltantes = [faltantes]
                                
                                if isinstance(faltantes, list):
                                    for item in faltantes:
                                        if item.strip(): st.write(f"• {item}")

                        # Dica Estratégica
                        if res.get('dicas'):
                            st.info(f"💡 **Diretriz de Governança:** {res['dicas']}")

            etapa_liberada = concluida 

        # Resumo do Ciclo Anual
        total = len(templates)
        concluidas = sum(status_final)
        p_val = concluidas / total if total > 0 else 0
        with container_progresso.container():
            col_p1, col_p2 = st.columns([4, 1])
            with col_p1:
                st.write(f"**Progresso Final do Ciclo:** {concluidas} de {total} etapas")
                st.progress(p_val)
            with col_p2:
                if p_val == 1.0:
                    st.balloons()
                    st.success("🏆 Ciclo Concluído!")

        if p_val == 1.0:
            st.info("🎉 **PARABÉNS!** Você completou a jornada de aceleração anual. Sua startup está pronta para novos desafios de governança e mercado.")

    finally:
        conn.close()

if __name__ == "__main__":
    Q4_page()