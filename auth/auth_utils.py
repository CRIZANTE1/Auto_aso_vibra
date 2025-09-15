import streamlit as st
import pandas as pd
from gdrive.gdrive_upload import GoogleDriveUploader
from gdrive.config import ADMIN_SHEET_NAME, SPREADSHEET_ID, ACCESS_REQUESTS_SHEET_NAME
from datetime import datetime

def is_oidc_available():
    try:
        return hasattr(st.user, 'is_logged_in')
    except Exception:
        return False

def is_user_logged_in():
    try:
        return st.user.is_logged_in
    except Exception:
        return False

def get_user_display_name():
    try:
        if hasattr(st.user, 'name'):
            return st.user.name
        elif hasattr(st.user, 'email'):
            return st.user.email
        return "Usuário"
    except Exception:
        return "Usuário"


def get_user_email() -> str | None:
    """Retorna o e-mail do usuário logado, normalizado para minúsculas."""
    try:
        if hasattr(st.user, 'email') and st.user.email:
            return st.user.email.lower().strip()
        return None
    except Exception:
        return None

@st.cache_data(ttl=600)
def get_permissions_df():
    """Carrega os dados de permissão da aba 'adm' da planilha principal."""
    try:
        uploader = GoogleDriveUploader()
        
        admin_data = uploader.get_data_from_sheet(ADMIN_SHEET_NAME)
        if admin_data and len(admin_data) >= 2:
            permissions_df = pd.DataFrame(admin_data[1:], columns=admin_data[0])
            permissions_df['email'] = permissions_df['email'].str.lower().str.strip()
            permissions_df['role'] = permissions_df['role'].str.lower().str.strip()
            return permissions_df
        
        return pd.DataFrame(columns=['email', 'nome', 'role'])

    except Exception as e:
        st.error(f"Erro crítico ao carregar dados de permissão: {e}")
        return pd.DataFrame()

def get_user_role():
    """Retorna o role do usuário logado. Retorna 'none' se não encontrado."""
    user_email = get_user_email()
    st.write(f"DEBUG: Email do usuário logado: {user_email}")

    if not user_email:
        return 'none' # Nenhum usuário logado

    permissions_df = get_permissions_df()
    st.write("DEBUG: DataFrame de Permissões lido da planilha:")
    st.dataframe(permissions_df)

    if permissions_df.empty:
        return 'none' # Nenhuma permissão configurada

    st.write("DEBUG: Comparando com o email do usuário...")
    st.write(permissions_df['email'] == user_email)

    user_entry = permissions_df[permissions_df['email'] == user_email]
    
    if not user_entry.empty:
        role = user_entry.iloc[0].get('role', 'none')
        st.write(f"DEBUG: Role encontrado: {role}")
        return role
    
    st.write("DEBUG: Nenhum role encontrado, retornando 'none'")
    return 'none' # Usuário não encontrado na lista de permissões

def create_access_request(email: str, name: str):
    """Cria uma nova solicitação de acesso na planilha."""
    try:
        uploader = GoogleDriveUploader()
        # Verifica se já existe uma solicitação pendente para este e-mail
        requests_data = uploader.get_data_from_sheet(ACCESS_REQUESTS_SHEET_NAME)
        if requests_data:
            df_requests = pd.DataFrame(requests_data[1:], columns=requests_data[0])
            if not df_requests[df_requests['email'] == email].empty:
                st.warning("Você já possui uma solicitação de acesso pendente.")
                return

        # Cria a nova solicitação
        new_request_data = [
            email,
            name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Pendente"
        ]
        uploader.append_data_to_sheet(ACCESS_REQUESTS_SHEET_NAME, [new_request_data])
        st.success("Sua solicitação de acesso foi enviada com sucesso! Um administrador irá revisá-la em breve.")
        st.balloons()

    except Exception as e:
        st.error(f"Ocorreu um erro ao enviar sua solicitação: {e}")
        raise

# --- Funções de verificação de permissão ---
def is_admin():
    return get_user_role() == 'admin'

def can_edit():
    return get_user_role() in ['admin', 'editor']

def can_view():
    return get_user_role() in ['admin', 'editor', 'viewer']

    st.cache_data.clear()
