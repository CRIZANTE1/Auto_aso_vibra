from operations.front import initial_page, page_config
import streamlit as st
from gdrive.config import SPREADSHEET_ID
from auth.login_page import show_login_page, show_logout_button
from auth.auth_utils import (
    is_user_logged_in, 
    get_user_role, 
    get_user_email, 
    get_user_display_name, 
    create_access_request
)

def main():
    page_config()

    # Define o ID da planilha na sessão no início da execução
    if 'current_spreadsheet_id' not in st.session_state:
        st.session_state['current_spreadsheet_id'] = SPREADSHEET_ID

    # Verifica se o ID da planilha foi configurado
    if not st.session_state.get('current_spreadsheet_id'):
        st.error("O ID da planilha principal não foi configurado no arquivo gdrive/config.py.")
        st.stop()

    # --- Lógica de Login e Permissão ---
    if not is_user_logged_in():
        show_login_page()
        st.stop()

    # Usuário está logado, verificar permissões
    show_logout_button()
    user_role = get_user_role()

    if user_role in ['admin', 'editor', 'viewer']:
        # Usuário com permissão: exibe a página principal
        page = initial_page()
        with st.sidebar:
            if st.button("Processar ASOs", key="btn_processar_sidebar"):
                page.processar_todos_cpfs()
        page.analisar_asos()
    else:
        # Usuário sem permissão: exibe a página de solicitação de acesso
        user_email = get_user_email()
        user_name = get_user_display_name()
        
        st.title("Solicitação de Acesso")
        st.write(f"Olá, {user_name} ({user_email}).")
        st.warning("Você ainda não tem permissão para acessar o sistema.")
        
        if st.button("Solicitar Acesso Agora"):
            create_access_request(user_email, user_name)

if __name__ == "__main__":
    main()
