# ARQUIVO: forms/q1_forms.py - Processador e Roteador do Q1

import streamlit as st
import time
from utils.db import update_status, save_submission_data, USUARIO_PADRAO_ID
from utils.agente_ia import configurar_gemini, validar_q1
from forms.diag_form import renderizar_diagnostico 
from forms.csd_canvas_form import renderizar_csd_canvas
from forms.analise_swot_form import renderizar_analise_swot
from forms.icp_form import renderizar_icp
from forms.jtbd_canvas_form import renderizar_jtbd_canvas
from forms.persona_01_form import renderizar_persona_01
from forms.persona_02_form import renderizar_persona_02
from forms.jornada_cliente_form import renderizar_jornada_cliente
from forms.matriz_atributos_form import renderizar_matriz_atributos
from forms.puv_form import renderizar_puv
from forms.tam_sam_som_form import renderizar_tam_sam_som

# ============================================================
# LÓGICA UNIFICADA DE PROCESSAMENTO DA SUBMISSÃO
# ============================================================
def processar_formulario(etapa_selecionada, dados_coletados, mapa_db):
    """
    Recebe os dados do formulário, valida com a IA e salva no banco de dados.
    """
    if not dados_coletados:
        st.error("Nenhum dado válido para envio.")
        return

    st.markdown("---")
    
    with st.spinner("🧠 O Agente IA está analisando sua submissão..."):
        try:
            # 1. Configura e chama o Agente IA
            client = configurar_gemini()
            resultado = validar_q1(client, dados_coletados)
            
            # 2. Exibe o feedback da IA
            st.subheader("📋 Feedback da Validação")
            
            # Mostra o resumo
            st.write(resultado.get("summary", "Análise concluída."))
            
            # Verifica se há falhas críticas
            pode_aprovar = True
            for v in resultado.get("validations", []):
                if v.get("ok"):
                    st.success(f"✅ {v['field']}: {v['reason']}")
                else:
                    st.error(f"❌ {v['field']}: {v['reason']}")
                    pode_aprovar = False
            
            # Exibe sugestões se houver
            if resultado.get("suggestions"):
                with st.expander("💡 Sugestões de Melhoria"):
                    for sug in resultado["suggestions"]:
                        st.write(f"- {sug}")

            # 3. Salvar no Banco de Dados se aprovado
            if pode_aprovar:
                campo_db = mapa_db.get(etapa_selecionada)
                
                # Salva os dados e a análise na tabela 'analises_ia'
                sucesso_save = save_submission_data(
                    usuario_id=USUARIO_PADRAO_ID,
                    etapa_nome=etapa_selecionada,
                    dados_form=dados_coletados,
                    analise_ia=resultado
                )
                
                if sucesso_save:
                    # Atualiza o checkmark de progresso
                    update_status(campo_db, 1)
                    st.balloons()
                    st.success(f"🚀 Etapa '{etapa_selecionada}' validada e salva com sucesso!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Erro ao persistir dados no banco de dados.")
            else:
                st.warning("⚠️ A IA identificou pontos obrigatórios pendentes. Ajuste o formulário e tente novamente.")

        except Exception as e:
            st.error(f"Erro crítico no processamento: {e}")

# ============================================================
# ROTEADOR DE FORMULÁRIOS
# ============================================================
def rotear_formulario(etapa_selecionada, mapa_db):
    """
    Direciona para o formulário correto baseado na seleção.
    """
    if etapa_selecionada == "1.0 Diagnóstico":
        renderizar_diagnostico(etapa_selecionada, mapa_db, processar_formulario)
    
    elif etapa_selecionada == "1.1 CSD Canvas":
        renderizar_csd_canvas(etapa_selecionada, mapa_db, processar_formulario)
        
    elif etapa_selecionada == "2.0 Análise SWOT":        
        renderizar_analise_swot(etapa_selecionada, mapa_db, processar_formulario)

    elif etapa_selecionada == "2.1 ICP":
        renderizar_icp(etapa_selecionada, mapa_db,processar_formulario)
        
    elif etapa_selecionada == "3.0 JTBD Canvas":
        renderizar_jtbd_canvas(etapa_selecionada, mapa_db, processar_formulario)
    
    elif etapa_selecionada == "3.1 Persona 01":
        renderizar_persona_01(etapa_selecionada, mapa_db, processar_formulario)
    
    elif etapa_selecionada == "3.1 Persona 02":
        renderizar_persona_02(etapa_selecionada, mapa_db,processar_formulario)
    
    elif etapa_selecionada == "3.2 Jornada do Cliente":
        renderizar_jornada_cliente(etapa_selecionada, mapa_db, processar_formulario)
    
    elif etapa_selecionada == "4.0 Matriz de Atributos":
         renderizar_matriz_atributos(etapa_selecionada, mapa_db, processar_formulario)  
    
    elif etapa_selecionada == "4.1 PUV":
         renderizar_puv(etapa_selecionada, mapa_db, processar_formulario)
    
    elif etapa_selecionada == "5.0 TAM SAM SOM":
        renderizar_tam_sam_som(etapa_selecionada, mapa_db, processar_formulario)
        
    else:
        st.warning(f"O formulário para '{etapa_selecionada}' ainda não foi mapeado no roteador.")