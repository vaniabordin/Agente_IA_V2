import streamlit as st
import pandas as pd
import os
from utils.db import (
    init_db, 
    conectar, 
    buscar_envios_startups, 
    verificar_etapa_concluida, 
    buscar_ultimo_feedback_ia
)
from utils.cadastro_usuario import exibir_usuarios_admin
from login import login, logout
from utils.criar_templates import cria_templates_page
from utils.ia_chat import mentoria_ia_sidebar
from utils.ui import aplicar_estilo_fcj
from utils.menu import renderizar_menu
from utils.ia_manager import ia_manager_page
from utils.consulta_resposta import aba_consulta_respostas

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
# Pega o caminho absoluto da pasta onde este arquivo (Home.py) está
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Monta o caminho para a imagem ignorando a pasta "app" no join, 
# pois o BASE_DIR já aponta para dentro dela
icon_path = os.path.join(BASE_DIR, "assets", "icone_fcj.png")

# Tente carregar a configuração. Se a imagem falhar, o app não trava.
try:
    st.set_page_config(
        page_title="Templates FCJ",
        layout="wide",
        page_icon=icon_path
    )
except Exception:
    # Caso a imagem ainda dê erro, carrega sem ícone para o app não parar
    st.set_page_config(
        page_title="Templates FCJ",
        layout="wide"
    )

# --- 2. INICIALIZAÇÃO E CONTROLE DE ACESSO ---

if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True
    
if "authenticated" not in st.session_state: 
    st.session_state["authenticated"] = False

# SE NÃO ESTIVER AUTENTICADO: Login
if not st.session_state["authenticated"]:
    # Mantemos o CSS para esconder o menu lateral
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarCollapseButton"], [data-testid="stHeader"] { 
                display: none !important; 
            }
        </style>
    """, unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 1.2, 1])
    with col_c: 
        # Adiciona a mensagem de carregamento antes de chamar o formulário
        with st.spinner("🚀 Carregando sistema..."):
            login()
    st.stop()

# --- 3. CONFIGURAÇÃO PARA USUÁRIOS LOGADOS ---
aplicar_estilo_fcj()

st.session_state["current_page"] = "home"

renderizar_menu()

# CSS customizado para cards e dashboard
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] { display: none !important; }
        .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #34394b; }
        .parecer-ia-box {
            border-left: 5px solid #00d4ff; 
            padding: 20px; 
            background-color: #1e2130; 
            border-radius: 8px;
            color: #ffffff !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE APOIO ---
@st.cache_data(ttl=60, show_spinner=False)
def calcular_progresso_trimestre(user_id, trimestre):
    conn = conectar()
    if not conn:
        return 0
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT nome_formulario FROM arquivos_templates WHERE template = %s AND status = 'ativo'", (trimestre,))
        etapas = cursor.fetchall()
        
        if not etapas: 
            return 0
        
        concluidas = sum([1 for e in etapas if verificar_etapa_concluida(user_id, e['nome_formulario'])])
        return (concluidas / len(etapas))
    except:
        return 0
    finally:
        conn.close()

def render_card_trimestre(titulo, progresso, pagina, status_bloqueado=False):
    partes = titulo.split(" - ")
    header_html = f"""
        <div style='min-height: 80px;'>
            <span style='font-size: 1.4rem; font-weight: bold; color: #00d4ff;'>{partes[0]}</span><br>
            <span style='font-size: 1rem; color: #a1a1a1;'>{partes[1] if len(partes)>1 else ''}</span>
        </div>
    """
    with st.container(border=True):
        st.markdown(header_html, unsafe_allow_html=True)
        if status_bloqueado:
            st.caption("🔒 Bloqueado")
            st.progress(0.0)
            st.button("Complete o anterior", key=f"btn_{titulo}", disabled=True, width="stretch")
        else:
            progresso_percent = int(progresso * 100)
            st.caption(f"Progresso: {progresso_percent}%")
            st.progress(progresso)
            if st.button("Acessar Jornada", key=f"btn_{titulo}", width="stretch", type="primary"):
                st.switch_page(pagina)

# --- 4. NAVEGAÇÃO POR ABAS ---
if st.session_state["role"] == "admin":
    titulos_abas = ["🏠 Home", "📁 Inserir Templates", "🧠 Inserir Conhecimento", "📝 Consulta de Respostas", "👥 Usuários"]
else:
    titulos_abas = ["🏠 Home"]

abas = st.tabs(titulos_abas)

# --- ABA: HOME ---
with abas[0]:
    if st.session_state["role"] == "aluno":      
        st.title(f"🚀 Olá, {st.session_state['user']}!")
        
        # Dados de Progresso
        uid = st.session_state["usuario_id"]
        p1 = calcular_progresso_trimestre(uid, "Q1")
        p2 = calcular_progresso_trimestre(uid, "Q2")
        p3 = calcular_progresso_trimestre(uid, "Q3")
        p4 = calcular_progresso_trimestre(uid, "Q4")
        media_global = (p1 + p2 + p3 + p4) / 4
        
        # Lógica de Foco
        if p1 < 1.0: ciclo, foco = "Q1 - Fundação", "Diagnóstico Estratégico"
        elif p2 < 1.0: ciclo, foco = "Q2 - Tração", "Validação de Canais"
        elif p3 < 1.0: ciclo, foco = "Q3 - Escala", "Eficiência Operacional"
        else: ciclo, foco = "Q4 - Estratégia", "Captação e Exit"

        # Métricas em Cards
        m1, m2, m3 = st.columns(3)
        m1.metric("Maturidade Global", f"{int(media_global * 100)}%")
        m2.metric("Ciclo Atual", ciclo)
        m3.metric("Foco Atual", foco)

        st.write("")
        st.subheader("📌 Sua Jornada de Evolução")
        c1, c2, c3, c4 = st.columns(4)
        with c1: render_card_trimestre("Q1 - Fundação", p1, "pages/Trimestre Q1.py")
        with c2: render_card_trimestre("Q2 - Tração", p2, "pages/Trimestre Q2.py", (p1 < 1.0))
        with c3: render_card_trimestre("Q3 - Escala", p3, "pages/Trimestre Q3.py", (p2 < 1.0))
        with c4: render_card_trimestre("Q4 - Estratégia", p4, "pages/Trimestre Q4.py", (p3 < 1.0))

        st.divider()
        st.subheader("🤖 Último Parecer da Mentoria IA")
        feedback = buscar_ultimo_feedback_ia(uid) 
        
        if feedback:
            cor = feedback.get('cor', '#00d4ff')
            st.markdown(f"""
                <div class="parecer-ia-box" style="border-left-color: {cor};">
                    <strong style="color: {cor};">Feedback IA ({feedback['data_avaliacao'].strftime('%d/%m/%Y')}):</strong><br>
                    <p style="font-style: italic; margin-top: 10px;">"{feedback['feedback_ludico']}"</p>
                </div>
            """, unsafe_allow_html=True)
        else:          
            st.info("💡 Envie seu primeiro template para que a IA possa analisar sua startup!")

    else:
        # Visão Admin
        st.title("📊 Painel de Controle FCJ")
        conn = conectar()
        if conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM usuarios WHERE role = 'aluno'")
            total_alunos = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM arquivos_templates")
            total_templates = cur.fetchone()[0]
            conn.close()
            
            a1, a2, a3 = st.columns(3)
            a1.metric("Startups Ativas", total_alunos)
            a2.metric("Templates no Sistema", total_templates)
            a3.metric("Ciclos Disponíveis", "Q1 - Q4")

# --- ABAS ADMIN ---
if st.session_state["role"] == "admin":
    with abas[1]: cria_templates_page()
    with abas[2]: ia_manager_page()
    with abas[3]:
        # Título da seção
        st.header("📝 Central de Monitoramento de Respostas")
        # 1. Visão Geral (Tabela Rápida)
        with st.expander("📊 Visão Geral de Envios (Tabela)", expanded=False):
            df_envios = buscar_envios_startups()
            if not df_envios.empty:
                st.dataframe(df_envios, width="stretch")
            else:
                st.info("Nenhuma startup enviou respostas ainda.")
        
        st.divider()

        # 2. Consulta Detalhada
        # Chama a função que cria no arquivo consulta_resposta.py
        aba_consulta_respostas()        
       
    with abas[4]:
        exibir_usuarios_admin()