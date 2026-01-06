import streamlit as st
import os
from utils.ia_chat import mentoria_ia_sidebar
from login import logout

def renderizar_menu():
    with st.sidebar:
        # Caminho dinâmico para a logo (ajustado para funcionar de qualquer subpasta)
        # O caminho busca a pasta 'assets' na raiz do projeto
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        raiz_projeto = os.path.dirname(diretorio_atual)
        logo_path = os.path.join(raiz_projeto, "assets", "logo_fcj_branca.png")
        
        if os.path.exists(logo_path):
            st.image(logo_path, width=200)
        else:
            # Fallback caso a imagem suma
            st.image("https://fcjventurebuilder.com/wp-content/themes/fcj/assets/images/logo-fcj-white.png", width=200)
        
        st.title("📌 Navegação")
        st.caption(f"👤 {st.session_state.get('user', 'Usuário')} | 🔐 {st.session_state.get('role', 'aluno')}")
        
        # Menu de links
        if st.session_state.get("role") != "admin":
            st.subheader("📖 Meus Trimestres")   
            st.page_link("Home.py", label="🏠 Home") 
            st.page_link("pages/Trimestre Q1.py", label="1️⃣ Trimestre Q1")
            st.page_link("pages/Trimestre Q2.py", label="2️⃣ Trimestre Q2")
            st.page_link("pages/Trimestre Q3.py", label="3️⃣ Trimestre Q3")
            st.page_link("pages/Trimestre Q4.py", label="4️⃣ Trimestre Q4")
            st.divider()
            
        # Chama a mentoria IA que você já tem
        mentoria_ia_sidebar()
        
        # Botão de Logout (o key deve ser único por página, ou use um valor dinâmico)
        if st.button("Sair / Logout", use_container_width=True, key=f"logout_sidebar_{st.session_state.get('usuario_id')}"):
            logout()