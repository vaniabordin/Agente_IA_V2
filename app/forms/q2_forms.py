# ARQUIVO: forms/q2_forms.py - Processador Unificado para Q2

import streamlit as st
import io
import json
from utils.db import update_status, save_submission_data, USUARIO_PADRAO_ID
from utils.agente_ia import analizar_documento_q2

def processar_formulario(etapa: str, db_field: str, file_bytes: io.BytesIO, file_name: str) -> tuple[bool, str]:
    """
    Processa o upload, chama a IA e persiste os dados no banco db_avaliacoes_ia.
    """
    
    st.info(f"🔍 Iniciando análise técnica: **{etapa}**...")
    
    try:
        # 1. Chamada para a IA (Gemini)
        # Passamos os bytes e o nome para a função que lida com o Vision/PDF
        with st.spinner(f"Analisando '{file_name}'..."):
            resultado_ia = analizar_documento_q2(etapa, file_bytes, file_name)
        
        if not resultado_ia:
            return False, "A IA retornou uma resposta vazia. Verifique a qualidade do arquivo."

        # 2. Persistência dos Dados
        
        # Simulamos o preenchimento dos dados do formulário para salvar na tabela 'analises_ia'
        dados_contexto = {
            "arquivo_origem": file_name,
            "etapa_selecionada": etapa,
            "projeto_id": USUARIO_PADRAO_ID
        }

        # Tentamos salvar a análise detalhada (JSON) e atualizar o progresso (Status 1)
        try:
            # Salva o log completo da submissão
            # A analise_ia aqui pode ser uma string ou dict dependendo do retorno do Gemini
            ia_log = {"feedback": resultado_ia} if isinstance(resultado_ia, str) else resultado_ia
            
            save_success = save_submission_data(
                usuario_id=USUARIO_PADRAO_ID,
                etapa_nome=etapa,
                dados_form=dados_contexto,
                analise_ia=ia_log
            )

            if save_success:
                # 3. Atualiza o status de progresso para 'Concluído' (1)
                update_status(db_field, 1)
                return True, resultado_ia
            else:
                return False, "Erro ao gravar os dados da análise no banco de dados."

        except Exception as db_ex:
            error_msg = f"IA aprovou, mas erro no Banco de Dados: {db_ex}"
            return False, error_msg

    except Exception as e:
        error_msg = f"Erro crítico no processamento da etapa {etapa}: {e}"
        st.error(error_msg)
        return False, error_msg