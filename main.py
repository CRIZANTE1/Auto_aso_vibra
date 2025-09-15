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

from datetime import datetime, timedelta

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
        # Instancia a página principal uma única vez
        page = initial_page()

        # --- Barra Lateral com Controles ---
        with st.sidebar:
            st.header("Controles")
            # Seletores de data
            data_inicio = st.date_input(
                "Data de Início", 
                value=datetime.now() - timedelta(days=365)
            )
            data_fim = st.date_input(
                "Data de Fim", 
                value=datetime.now()
            )

            # Botão de processamento visível apenas para admin e editor
            if user_role in ['admin', 'editor']:
                if st.button("Processar ASOs", key="btn_processar_sidebar", type="primary"):
                    if data_inicio > data_fim:
                        st.error("A data de início não pode ser maior que a data de fim.")
                    else:
                        # A chamada para processar usa a instância 'page' já criada.
                        # A própria função irá forçar o recarregamento da página.
                        page.processar_todos_cpfs(data_inicio, data_fim)
            else:
                st.info("Você tem permissão de visualização. Para processar novos dados, contate um administrador.")

        # --- Exibição da Página Principal ---
        # A análise é sempre exibida com os dados mais recentes da planilha.
        # Após o processamento, a página é recarregada e esta função é executada novamente.
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
