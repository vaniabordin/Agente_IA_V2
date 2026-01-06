import streamlit as st
import os
import plotly.graph_objects as go

def aplicar_estilo_fcj():
    """Lê o arquivo CSS e aplica ao markdown do Streamlit"""
    # Tenta encontrar o arquivo independente de onde o script é chamado
    caminhos_possiveis = [
        os.path.join("app", "assets", "style.css"),
        os.path.join("assets", "style.css"),
        "style.css"
    ]
    
    for caminho in caminhos_possiveis:
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            return True
    return False

def criar_grafico_circular(porcentagem):
    cor_azul_fcj = "#00ADEF"
    cor_fundo_grafico = "#113140"
    
    fig = go.Figure(go.Pie(
        values=[porcentagem, 100 - porcentagem],
        marker_colors=[cor_azul_fcj, cor_fundo_grafico],
        textinfo='none',
        hoverinfo='none',
        sort=False,
        hole=0.75
    ))
    
    fig.update_layout(
            showlegend=False,
            margin=dict(t=0, b=0, l=0, r=0), 
            height=200,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            # Adiciona o texto centralizado
            annotations=[dict(
                text=f'{porcentagem}%', 
                x=0.5, y=0.5, 
                font_size=24, 
                font_color=cor_azul_fcj,
                showarrow=False
            )]
    )
    return fig