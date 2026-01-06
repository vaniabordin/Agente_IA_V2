# ARQUIVO: forms/q1_forms.py

import streamlit as st
import time 

# IMPORTANTE: Você precisa garantir que estas importações funcionem:
# 1. db: Seu módulo de utilidades de banco de dados (que tem mark_completed)
# 2. agente_ia: Seu módulo Gemini (que tem configurar_gemini e validar_q1)
from utils import db 
from utils.agente_ia import configurar_gemini, validar_q1 

# ============================================================
# LÓGICA UNIFICADA DE PROCESSAMENTO DA SUBMISSÃO
# ============================================================
def processar_formulario(etapa_selecionada, dados_coletados, mapa_db):
    """Lógica unificada de chamada à IA, exibição de resultados e salvamento no DB."""
    
    if not dados_coletados:
        st.error("Nenhum dado válido para envio.")
        return

    st.markdown("---")
    
    # 1. Chamar o Agente IA para validar (com o sistema de retry)
    try:
        model = configurar_gemini()
    except Exception as e:
        st.error(f"Erro ao configurar Gemini (Verifique a API Key): {e}")
        return
        
    # Usando st.expander para conter o spinner e o resultado da IA
    with st.expander("🔬 Resultados da Análise da IA", expanded=True):
        
        with st.spinner("Validando dados com a Inteligência Artificial..."):
            # Chama a função de validação robusta
            agent_response = validar_q1(model, dados_coletados) 
        
        # 2. Exibir o resultado
        
        # Sua lógica de aprovação (baseada no JSON de validação da IA)
        aprovado = all(v.get("ok", False) for v in agent_response.get("validations", []))
        
        if aprovado:
            st.success("✅ Etapa APROVADA! Dados consistentes e completos.")
            st.balloons()
        else:
            st.error("❌ Etapa Rejeitada! Melhorias necessárias.")

        # Exibir sugestões da IA e validações detalhadas
        st.markdown("##### Detalhes da Validação:")
        for validation in agent_response.get("validations", []):
            icone = "✅" if validation.get("ok", False) else "❌"
            # Formatação baseada no layout: 
            st.markdown(f"**{icone} {validation['field']}:** {validation['reason']}")
            
        if agent_response.get("suggestions"):
            st.markdown("##### Sugestões Gerais:")
            for suggestion in agent_response.get("suggestions", []):
                st.info(f"💡 {suggestion}")

        # Opcional: Mostrar o JSON completo para debug
        # st.json(agent_response) 


    # 3. Salvar o progresso se aprovado
    if aprovado:
        campo_db = mapa_db.get(etapa_selecionada)
        if campo_db:
            # Chama a função de conclusão do seu módulo DB
            db.mark_completed(1, campo_db) # Assumindo ID do Projeto = 1
            st.success("Progresso salvo no banco de dados! Retornando em 3 segundos...")
            time.sleep(3)
            
            # Limpa o state para voltar à tela de botões (força re-renderização)
            st.session_state.etapa_selecionada = None
            st.rerun() # Use st.rerun() em vez de st.stop() + st.session_state.clear()
            
            
# ============================================================
# FORMULÁRIOS ESPECÍFICOS: 1.0 DIAGNÓSTICO
# ============================================================

# ... (Partes anteriores do código - Lógica Unificada e Seção 1 estão OK) ...

def formulario_diagnostico(etapa_selecionada, mapa_db):
    """Renderiza o formulário 1.0 Diagnóstico."""
    
    st.subheader(f"Preencha as informações da etapa: **{etapa_selecionada}**")
    
    with st.form(key="form_diagnostico"):
        
        # 1. IDENTIFICAÇÃO E CONTEXTO (Mantida)
        # ... (Seção 1. Identificação e Contexto está OK) ...
        st.markdown("##### 1. Identificação e Contexto")
        col_id_1, col_id_2 = st.columns(2)
        with col_id_1:
            nome = st.text_input("Nome da Startup*", key="diag_nome")
            fundadores = st.text_input("Fundadores", key="diag_fundadores")
            setor = st.text_input("Setor / Segmento*", key="diag_setor")
            responsavel = st.text_input("Responsável", key="diag_responsavel")
        with col_id_2:
            data_inicio = st.text_input("Data de Início (Q1)", key="diag_data_inicio")
            noth_star_metric = st.text_input("North Star Metric", key="diag_north_star_metric")
            objetivo_programa = st.text_input("Objetivo com o Programa", key="diag_objetivo_programa")
            meta_chave = st.text_input("Meta-Chave (até Q4)", key="diag_meta_chave")     
        
        # 2. CONTEXTO ESTRATÉGICO (CORRIGIDO E OTIMIZADO)
        st.markdown("##### 2. Contexto Estratégico")
        st.markdown("**Produto e Estágio**")
        
        # Opções para Selectbox
        opcoes_estagio = [
            "Selecione o Estágio",
            "MVP",
            "Pós-MVP",
            "Tração",
            "Pré-captação",
            "Escala"
        ]
        
        opcoes_receita = [
            "Selecione o Modelo",
            "Recorrente",
            "Pontual",
            "Licenciamento",
            "Freemium",
            "Comissão",
            "Pay-per-use",
            "SaaS (software as a Service)",
            "Assinatura",
            "Outros"            
        ]
        
        # Linha 1: Investimento e Validação
        col_est_l1_1, col_est_l1_2 = st.columns(2)
        with col_est_l1_1:
            captou_investimento = st.text_input("Já captou investimento?", key="diag_captou_investimento")
        with col_est_l1_2:
            produto_validado = st.text_input("Possui produto validado?", key="diag_produto_validado")
            
        # Linha 2: Problemas e Estágio Atual
        col_est_l2_1, col_est_l2_2 = st.columns(2)
        with col_est_l2_1:
            problemas_principais = st.text_input("Quais problemas principais ele resolve?", key="diag_problemas_principais")
        with col_est_l2_2:
            # CORREÇÃO APLICADA AQUI: Adicionado 'options=opcoes_estagio'
            estagio_atual = st.selectbox(
                "Estágio atual", 
                options=opcoes_estagio, 
                key="diag_estagio_atual"
            )
             
            
        # Linha 3: Modelo de Receita (Selectbox) e Outros (AJUSTADO PARA PROPORÇÃO 1:1)
        # Usamos st.columns(2) para garantir que cada campo ocupe 50%
        col_est_l3_1, col_est_l3_2 = st.columns(2)         
        with col_est_l3_1:
            modelo_receita = st.selectbox(
                "Modelo de receita", 
                options=opcoes_receita, 
                key="diag_modelo_receita"
            )
            
        with col_est_l3_2:
            # CORREÇÃO: Renderiza o campo sempre, mas desabilita se não for "Outros"
            # Isso garante o alinhamento e o estado consistente.
            is_disabled = (modelo_receita != "Outros")
            
            outros = st.text_input(
                "Outros, quais", 
                key="diag_outros",
                disabled=is_disabled
            )
            
            if is_disabled:
                outros = "" # Limpa a variável se o campo estiver desabilitado

        # Linha 4: Aquisição e CAC/LTV
        col_est_l4_1, col_est_l4_2 = st.columns(2)
        with col_est_l4_1:
            canal_principal_aquisicao = st.text_input("Canal principal de aquisição hoje", key="diag_canal_aquisicao")
        with col_est_l4_2:
            conhece_seu_CAT_LTV = st.text_input("Conhece seu CAC e LTV?", key="diag_conhece_cat_ltv")
            
        # BOTÃO DE SUBMISSÃO
        submitted = st.form_submit_button("Enviar para Validação da IA")

    if submitted:
        # ... (O bloco de coleta de dados 'dados_coletados' está OK para o novo layout) ...
        dados_coletados = {
             "etapa": etapa_selecionada,
             "identificacao": {
                 "nome": nome,
                 "fundadores": fundadores,
                 "setor": setor,
                 "responsavel": responsavel,
                 "data_inicio": data_inicio,
                 "noth_star_metric": noth_star_metric,
                 "objetivo_programa": objetivo_programa,
                 "meta_chave": meta_chave
             },
             "produto_e_estagio": {
                 "captou_investimento": captou_investimento,
                 "produto_validado": produto_validado,  
                 "problemas_principais": problemas_principais,
                 "modelo_receita": modelo_receita,
                 "estagio_atual": estagio_atual,
                 "canal_principal_aquisicao": canal_principal_aquisicao,
                 "conhece_seu_CAT_LTV": conhece_seu_CAT_LTV,
                 "outros": outros              
             },
             "recursos": {} 
        }
        processar_formulario(etapa_selecionada, dados_coletados, mapa_db)
        
        
        
        
          # Linha 1 : MRR    
        st.markdown("**MRR**")            
        col_mr, col_mr_obs = st.columns(2)
        with col_mr:
           # mr_r = st.text_input("MRR", key="met_mrr", value="R$", label_visibility="collapsed")
            mr_r = st.text_input("MRR", key="met_mrr", label_visibility="collapsed")
        with col_mr_obs:
            mr_r_obs = st.text_input("Observação MRR", key="obs_mrr", label_visibility="collapsed")
        
        # Linha 2 : Nº de clientes pagantes
        st.markdown("**Nº de Clientes Pagantes**")
        col_clientes, col_clientes_obs = st.columns(2)
        with col_clientes:
            n_clientes = st.text_input("Nº de clientes pagantes", key="met_clientes", label_visibility="collapsed")
        with col_clientes_obs:
            n_clientes_obs = st.text_input("Observação Clientes", key="obs_clientes", label_visibility="collapsed")
        
        # Linha 3: Ticket Médio / ARR
        st.markdown("**Ticket Médio / ARR**")
        col_ticket, col_ticket_obs = st.columns(2)
        with col_ticket:
            ticket_medio = st.text_input("Ticket médio / ARR estimado", key="met_ticket", value="R$", label_visibility="collapsed")
        with col_ticket_obs:
            ticket_medio_obs = st.text_input("Observação Ticket", key="obs_ticket", label_visibility="collapsed")
        
        #Linha 4: CAC (Custo de Aquisição de Clientes) estimado
        st.markdown("**CAC (Custo de Aquisição de Clientes) estimado**")
        col_cac, col_cac_obs = st.columns(2)
        with col_cac:
            cac_custo = st.text_input("CAC (Custo de Aquisição de Clientes) estimado", key="met_cac", value="R$", label_visibility="collapsed")
        with col_cac_obs:
            cac_custo_obs = st.text_input("Observação CAC", key="obs_cac", label_visibility="collapsed")

        # Linha 5: LTV (Lifetime Value) estimado
        st.markdown("**LTV (Lifetime Value) estimado**")
        col_ltv, col_ltv_obs = st.columns(2)
        with col_ltv:
            ltv_valor = st.text_input("LTV (Lifetime Value) estimado", key="met_ltv", value="R$", label_visibility="collapsed")
        with col_ltv_obs:
            ltv_valor_obs = st.text_input("Observação LTV", key="obs_ltv", label_visibility="collapsed")
            
         # Linha 6 : Churn médio mensal
        st.markdown("**Churn Médio Mensal**")
        col_churn, col_churn_obs = st.columns(2)
        with col_churn:
            churn_mensal = st.text_input("Churn médio mensal", key="met_churn", value="%", label_visibility="collapsed")
        with col_churn_obs:
            churn_mensal_obs = st.text_input("Observação Churn", key="obs_churn", label_visibility="collapsed")
        
        #   Linha 7: Número de leads/mês
        st.markdown("**Número de leads/mês**")
        col_leads, col_leads_obs = st.columns(2)
        with col_leads:
            n_leads = st.text_input("Número de leads/mês", key="met_leads", label_visibility="collapsed")
        with col_leads_obs:
            n_leads_obs = st.text_input("Observação Leads", key="obs_leads", label_visibility="collapsed")   
        
        # Linha 8: CPL (Custo por Lead)
        st.markdown("**CPL (Custo por Lead)**")
        col_cpl, col_cpl_obs = st.columns(2)
        with col_cpl:
            cpl_custo = st.text_input("CPL (Custo por Lead)", key="met_cpl", value="R$", label_visibility="collapsed")
        with col_cpl_obs:
            cpl_custo_obs = st.text_input("Observação CPL", key="obs_cpl",label_visibility="collapsed")            
        
        # Linha 9: Visitas no Site/mês
        st.markdown("**Visitas no Site/mês**")
        col_visitas, col_visitas_obs = st.columns(2)
        with col_visitas:
            n_visitas = st.text_input("Visitas no Site/mês", key="met_visitas", label_visibility="collapsed")
        with col_visitas_obs:
            n_visitas_obs = st.text_input("Observação Visitas", key="obs_visitas", label_visibility="collapsed")

        # Linha 10: Número de LP's ativas
        st.markdown("**Número de LP's ativas**")
        col_lp, col_lp_obs = st.columns(2)
        with col_lp:
            n_lp = st.text_input("Número de LP's ativas", key="met_lp", label_visibility="collapsed")
        with col_lp_obs:
            n_lp_obs = st.text_input("Observação LPs", key="obs_lp", label_visibility="collapsed")

        # Linha 11: Campanhas rodando
        st.markdown("**Campanhas rodando**")
        col_campanhas, col_campanhas_obs = st.columns(2)
        with col_campanhas:
            n_campanhas = st.text_input("Campanhas rodando", key="met_campanhas", label_visibility="collapsed")
        with col_campanhas_obs:
            n_campanhas_obs = st.text_input("Observação Campanhas", key="obs_campanhas", label_visibility="collapsed")

        # Linha 12: Testes de canal executados
        st.markdown("**Testes de canal executados**")   
        col_testes, col_testes_obs = st.columns(2)
        with col_testes:
            n_testes = st.text_input("Testes de canal executados", key="met_testes", label_visibility="collapsed")
        with col_testes_obs:
            n_testes_obs = st.text_input("Observação Testes", key="obs_testes", label_visibility="collapsed")            
        
        # Linha 13: NPS
        st.markdown("**NPS**")
        col_nps, col_nps_obs = st.columns(2)
        with col_nps:
            nps = st.text_input("NPS", key="met_nps", label_visibility="collapsed")
        with col_nps_obs:
            nps_obs = st.text_input("Observação NPS", key="obs_nps", label_visibility="collapsed")
            
            
            
            #Q1.py
            
            # ARQUIVO: pages/Q1.py (VERSÃO FINAL COM INTEGRAÇÃO DE CHAT)

import streamlit as st
from pathlib import Path

# IMPORTAÇÕES ESSENCIAIS DA NOVA ARQUITETURA
from utils import db # Seu módulo DB
from forms.q1_forms import formulario_diagnostico # Formulário da etapa 1.0

# NOVAS IMPORTAÇÕES PARA O CHAT E VALIDAÇÃO DA IA
from utils.agente_ia import configurar_gemini, gerar_resposta_chat # <--- IMPORTAÇÕES CHAVE

# ------------------------------------------------
# MAPAS E FLUXO
# ------------------------------------------------
ETAPAS = [
    ["Cronograma"],
    ["1.0 Diagnóstico", "1.1 CSD Canvas"],
    ["2.0 Análise SWOT", "2.1 ICP"],
    ["3.0 JTBD Canvas", "3.1 Persona 01", "3.1 Persona 02", "3.2 Jornada do Cliente"],
    ["4.0 Matriz de Atributos", "4.1 PUV"],
    ["5.0 TAM SAM SOM", "5.1 Benchmarking", "5.2 Canvas de Diferenciação"],
    ["6.0 Golden Circle", "6.1 Posicionamento Verbal"],
    ["7.0 Arquetipo", "7.1 Slogan"],
    ["8.0 Consciência da Marca", "8.1 Materiais visuais"],
    ["9.0 Diagrama de Estratégia"],
    ["10.0 Meta SMART", "10.1 OKRs e KPIs", "10.2 Bullseyes Framework"],
    ["11.0 Briefing Campanha", "11.1 Roadmap"]

]

MAPA_DB = {
    "Cronograma": "cronograma_ok",
    "1.0 Diagnóstico": "diagnostico_ok",
    "1.1 CSD Canvas": "csd_canvas_ok",
    "2.0 Análise SWOT": "swot_ok",
    "2.1 ICP": "icp_ok",
    "3.0 JTBD Canvas": "jtbd_ok",
    "3.1 Persona 01": "persona1_ok",
    "3.1 Persona 02": "persona2_ok",
    "3.2 Jornada do Cliente": "jornada_ok",
    "4.0 Matriz de Atributos": "atributos_ok",
    "4.1 PUV": "puv_ok",
    "5.0 TAM SAM SOM": "tam_ok",
    "5.1 Benchmarking": "benchmarking_ok",
    "5.2 Canvas de Diferenciação": "canvas_diferenciacao_ok",
    "6.0 Golden Circle": "golden_ok",
    "6.1 Posicionamento Verbal": "posicionamento_ok",
    "7.0 Arquetipo": "arquetipo_ok",
    "7.1 Slogan": "slogan_ok",
    "8.0 Consciência da Marca": "consciencia_marca_ok",
    "8.1 Materiais visuais": "materiais_visuais_ok",
    "9.0 Diagrama de Estratégia": "diagrama_ok",
    "10.0 Meta SMART": "meta_ok",
    "10.1 OKRs e KPIs": "okrs_ok",
    "10.2 Bullseyes Framework": "bullseyes_ok",
    "11.0 Briefing Campanha": "briefing_ok",
    "11.1 Roadmap": "roadmap_ok"
}

# ------------------------------------------------
# FUNÇÕES DE ESTADO E INICIALIZAÇÃO
# ------------------------------------------------
def init_state_once():
    if "initialized" not in st.session_state:
        st.session_state.clear()
        st.session_state["initialized"] = True
        st.session_state.etapa_selecionada = None
        st.session_state.ultima_etapa_chat = None # Adicionado para controlar o chat
        st.session_state["chat_messages"] = []

# ------------------------------------------------
# CHAT DE SUPORTE (Para Sidebar) - AGORA COM INTEGRAÇÃO REAL
# ------------------------------------------------
def renderizar_chat_suporte(etapa_selecionada):
    """Renderiza a caixa de chat usando o st.session_state para histórico."""
    
    # 1. Checa se o chat precisa ser reiniciado
    if st.session_state.get('ultima_etapa_chat') != etapa_selecionada:
        # Mensagem inicial do assistente
        st.session_state["chat_messages"] = [{"role": "model", "content": f"Olá! Sou seu assistente de IA. Pergunte o que quiser sobre o preenchimento da etapa **'{etapa_selecionada}'**."}]
        st.session_state['ultima_etapa_chat'] = etapa_selecionada

    # 2. Renderiza o histórico de mensagens
    for message in st.session_state["chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 3. Input do Usuário e Geração de Resposta
    if prompt := st.chat_input("O que você gostaria de saber sobre esta etapa?"):
        
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("model"):
            with st.spinner("IA pensando..."):
                
                # --- INTEGRAÇÃO REAL COM GEMINI ---
                try:
                    # 1. Configura o modelo (usa cache do Streamlit para eficiência)
                    @st.cache_resource
                    def get_gemini_model():
                        return configurar_gemini()
                    
                    model = get_gemini_model()
                    
                    # 2. Gera a resposta usando o histórico e contexto
                    response_text = gerar_resposta_chat(
                        model, 
                        st.session_state["chat_messages"], # Passa o histórico
                        etapa_selecionada # Passa o contexto
                    )
                except Exception as e:
                    response_text = f"❌ Erro na IA: Falha ao conectar/quota esgotada. Erro: {e}"
                    print(response_text)
                
                st.markdown(response_text)
                
        st.session_state["chat_messages"].append({"role": "model", "content": response_text})


# ------------------------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------------------------
def main():
    init_state_once()
    
    st.set_page_config(layout="wide") # Layout wide para acomodar a sidebar
    
    # ---------------------------
    # INTEGRAÇÃO DO STYLE.CSS AQUI
    # ---------------------------
    css_file = Path(__file__).parent.parent / "assets" / "style.css"
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    
    st.title("Validação do Template Q1")
    st.info("Fluxo completo de validação dos 12 módulos Q1. Use a barra lateral para suporte IA.")

    # Inicializa DB e pega status
    db.init_db()
    status = db.get_progress(1) # Assumindo ID do Projeto = 1

    # ... (Sua lógica para descobrir qual etapa está liberada - etapa_idx) ...
    etapa_idx = 0 # Simulação para teste (ajuste se precisar de lógica real)

    # ---------------------------
    # BARRA LATERAL (OPERAÇÃO E CHAT)
    # ---------------------------
    with st.sidebar:
        st.markdown("### Navegação Rápida")
        if st.session_state.etapa_selecionada:
             st.markdown(f"**Etapa Atual:** {st.session_state.etapa_selecionada}")

        st.divider()

        # O chat só é renderizado se uma etapa foi selecionada
        if st.session_state.etapa_selecionada:
            st.subheader(f"💬 Ajuda Contextual")
            renderizar_chat_suporte(st.session_state.etapa_selecionada)
        else:
            st.info("Selecione uma etapa para iniciar o suporte da IA.")
            
    # ---------------------------
    # CORPO PRINCIPAL
    # ---------------------------

# ---------------------------
    # 1. BOTÕES DAS ETAPAS (Ajustado para 1 botão por linha / Largura total)
    # ---------------------------
    if st.session_state.etapa_selecionada is None:
        st.info("Clique em uma etapa para começar o upload do arquivo e validação")
        
        # Iteramos sobre todos os grupos de etapas
        for grupo in ETAPAS:
            
            # Iteramos sobre cada nome de etapa dentro do grupo
            for nome in grupo:
                key_btn = f"btn_{nome.replace(' ', '_')}"
                
                # Obtém o status de conclusão do banco de dados (MAPA_DB)
                campo_db = MAPA_DB.get(nome, 'invalid_key')
                is_completed = status.get(campo_db, False)

                # Verifica se a etapa faz parte da etapa liberada atual
                # A lógica abaixo garante que apenas etapas do módulo liberado (ou anteriores) estejam ativas
                # Vamos simplificar para focar na aparência, mas o código original pode ter uma lógica de 'etapa_idx' mais complexa
                
                # Para fins de layout, vamos desabilitar se já estiver completa
                disabled_state = is_completed 
                
                clicado = st.button(
                    f"✅ {nome}" if is_completed else nome, # Adiciona um checkmark se completa
                    disabled=disabled_state,
                    key=key_btn
                )
                
                if clicado:
                    st.session_state.etapa_selecionada = nome
                    st.session_state.uploaded_file = None # Limpa o arquivo anterior, se houver
                    st.stop() # Interrompe a renderização para recarregar a página com a etapa selecionada
   

    # 2. FORMULÁRIO E VALIDAÇÃO DA ETAPA SELECIONADA
    etapa_selecionada = st.session_state.etapa_selecionada

    # Botão Voltar (Permanece no corpo principal, no topo da etapa)
    if st.button("⬅ Voltar para a Visão Geral das Etapas"):
        st.session_state.etapa_selecionada = None
        st.rerun()

    st.divider()
    
    # Mapeamento para o formulário específico
    if etapa_selecionada == "1.0 Diagnóstico":
        formulario_diagnostico(etapa_selecionada, MAPA_DB)
        
    elif etapa_selecionada == "1.1 CSD Canvas":
        st.warning(f"Formulário para {etapa_selecionada} em desenvolvimento.")
        # formulario_csd_canvas(etapa_selecionada, MAPA_DB)
        
    # ... (Adicione um elif para cada etapa) ...
    
    else:
        st.info(f"Formulário para '{etapa_selecionada}' em construção.")


if __name__ == "__main__":
    main()
    
    
    ##Home.py
    # ARQUIVO: home.py - Arquivo principal da aplicação Streamlit (Home)

import streamlit as st

# 1. IMPORTAÇÕES
# Importa o roteador centralizado dos seus formulários, que está no módulo forms/q1_forms.py
from forms.q1_forms import rotear_formulario 
# Importa o módulo de banco de dados
from utils import db

# ==========================================================
# 2. CONFIGURAÇÕES GLOBAIS DA PÁGINA (Sempre as primeiras chamadas)
# ==========================================================
st.set_page_config(
    page_title="Templates FCJ - Growth Program",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# 🛑 3. INICIALIZAÇÃO DO BANCO DE DADOS 🛑
# ==========================================================

# Chamamos init_db() aqui. O Streamlit executará este bloco
# na primeira carga e em cada re-execução, mas a lógica interna
# do init_db (CREATE TABLE IF NOT EXISTS) garante que ele só
# altere o DB na primeira vez.
db.init_db()

# ==========================================================
# 4. DADOS FIXOS: MAPA DE ETAPAS E DB
# ==========================================================
# Mapeamento do menu para os campos do banco de dados (usado para salvar o progresso)
MAPA_DB_ETAPAS = {
    "1.0 Diagnóstico": "q1_diagnostico_completo",
    "2.0 OKRs e KPIs": "q2_okrs_e_kpis",
    "3.0 Estruturação de Growth": "q3_estrutura_growth",
    "4.0 Roadmap e Testes": "q4_roadmap_testes",
    # Adicione mais etapas aqui à medida que você cria novos formulários.
}

# Define a etapa inicial no estado da sessão
if 'etapa_selecionada' not in st.session_state:
    st.session_state.etapa_selecionada = "1.0 Diagnóstico"

# ==========================================================
# 5. HEADER E INTRODUÇÃO
# ==========================================================
st.title("🚀 Dashboard de Acompanhamento Trimestral")
st.write("---")
st.markdown("""
    Preencha as informações detalhadas de cada etapa do programa usando o menu lateral. 
    **Todos os formulários são validados por uma I.A. após a submissão.**
""")
st.write("---")

# ==========================================================
# 6. BARRA LATERAL (ROTEAMENTO)
# ==========================================================

st.sidebar.title("🛠️ Etapas do Q1")
st.sidebar.markdown("Selecione a etapa para preenchimento e análise:")

# Cria o seletor de etapas na barra lateral, sincronizado com st.session_state
opcoes_etapas = list(MAPA_DB_ETAPAS.keys())
index_inicial = opcoes_etapas.index(st.session_state.etapa_selecionada) if st.session_state.etapa_selecionada in opcoes_etapas else 0

etapa_selecionada_menu = st.sidebar.radio(
    "Escolha a Etapa",
    options=opcoes_etapas,
    index=index_inicial,
    key='etapa_selecionada_menu_radio' # Usamos uma chave diferente para o radio, mas atualizamos 'etapa_selecionada' abaixo
)

# Atualiza st.session_state.etapa_selecionada para o valor selecionado
st.session_state.etapa_selecionada = etapa_selecionada_menu

# ==========================================================
# 7. SEÇÃO DE AJUDA E AGENTE I.A. LATERAL (ADICIONADO)
# ==========================================================

st.sidebar.markdown("---")
st.sidebar.subheader(f"💬 Ajuda I.A. - {st.session_state.etapa_selecionada}")

st.sidebar.info("""
    O **Agente I.A.** está aqui para te guiar no preenchimento. 
    Use este campo para tirar dúvidas específicas sobre o nível 
    de detalhe ou os critérios de validação para a etapa atual.
""")

# Simulação das Perguntas Frequentes (FAQs)
st.sidebar.markdown("**Perguntas Frequentes:**")
st.sidebar.markdown(
    """
    * ❓ Qual o critério de nota 4 ('Escalável') para os itens de maturidade?
    * ❓ Meu Produto/Serviço atende a todos os critérios?
    * ❓ Meu LTV/CAC e apenas estimado, posso preencher?
    """
)

# Campo de texto para interação com a I.A. (Simulação de Chat)
pergunta_usuario = st.sidebar.text_input(
    "Pergunte ao Agente I.A.:",
    key="ai_sidebar_query",
    placeholder="Ex: O que é a matriz de maturidade?"
)

if pergunta_usuario:
    # Esta é a área onde a lógica real de chat seria implementada,
    # chamando o Agente I.A. para responder à pergunta.
    st.sidebar.warning(f"Processando pergunta: '{pergunta_usuario}'... A funcionalidade de chat está em desenvolvimento!")

# ==========================================================
# 8. CHAMADA DO ROTEADOR DE FORMULÁRIOS
# ==========================================================

# A função rotear_formulario (importada de forms/q1_forms.py) 
# é chamada para renderizar o formulário correto com base na seleção do usuário.
if st.session_state.etapa_selecionada:
    rotear_formulario(st.session_state.etapa_selecionada, MAPA_DB_ETAPAS)