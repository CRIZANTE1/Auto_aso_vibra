import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import streamlit as st
import tempfile
from gdrive.config import get_credentials_dict, MATRIX_SHEETS_ID

class GoogleDriveUploader:
    def __init__(self, is_matrix=False):
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        self.credentials = None
        self.drive_service = None
        self.sheets_service = None
        self.initialize_services()
        
        # --- LÓGICA DE SELEÇÃO DE ID ---
        if is_matrix:
            # Se for uma operação na matriz, usa o ID fixo da matriz
            self.spreadsheet_id = MATRIX_SHEETS_ID
            self.folder_id = None # Ações na matriz não devem fazer upload de arquivos
        else:
            # Para operações normais, pega os IDs da sessão do usuário
            self.spreadsheet_id = st.session_state.get('current_spreadsheet_id')
            self.folder_id = st.session_state.get('current_folder_id')

    def initialize_services(self):
        try:
            credentials_dict = get_credentials_dict()
            self.credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=self.SCOPES
            )
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
        except Exception as e:
            st.error(f"Erro ao inicializar serviços do Google: {str(e)}")
            raise



    def append_data_to_sheet(self, sheet_name, data_rows):
        if not self.spreadsheet_id:
            st.error("ID da planilha da Unidade Operacional não definido na sessão.")
            return None
        try:
            # Garante que data_rows seja uma lista de listas
            if not isinstance(data_rows, list) or not all(isinstance(row, list) for row in data_rows):
                # Se for uma única linha (uma lista simples), envolve-a em outra lista
                if isinstance(data_rows, list):
                    data_rows = [data_rows]
                else:
                    st.error("Formato de dados inválido para append. Deve ser uma lista de linhas.")
                    return None

            range_name = f"{sheet_name}!A:Z"
            body = {
                'values': data_rows
            }
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            return result
        except Exception as e:
            st.error(f"Erro ao adicionar dados à planilha '{sheet_name}': {str(e)}")
            raise

    def get_data_from_sheet(self, sheet_name):
        if not self.spreadsheet_id:
            st.error("ID da planilha da Unidade Operacional não definido na sessão.")
            return []
        try:
            range_name = f"{sheet_name}!A:Z"
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            values = result.get('values', [])
            return values
        except Exception as e:
            st.error(f"Erro ao ler dados da planilha '{sheet_name}': {str(e)}")
            raise

    def update_cells(self, sheet_name, range_name, values):
        if not self.spreadsheet_id:
            st.error("ID da planilha da Unidade Operacional não definido na sessão.")
            return None
        try:
            body = {
                'values': values
            }
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{range_name}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            return result
        except Exception as e:
            st.error(f"Erro ao atualizar células na planilha '{sheet_name}': {str(e)}")
            raise
            
    def create_new_spreadsheet(self, name):
        """Cria uma nova Planilha Google e retorna seu ID."""
        try:
            spreadsheet_body = {'properties': {'title': name}}
            spreadsheet = self.sheets_service.spreadsheets().create(body=spreadsheet_body, fields='spreadsheetId').execute()
            st.info(f"Planilha '{name}' criada com sucesso.")
            return spreadsheet.get('spreadsheetId')
        except Exception as e:
            st.error(f"Erro ao criar nova planilha: {e}")
            raise

    def setup_sheets_in_new_spreadsheet(self, spreadsheet_id, sheets_config):
        """Cria as abas e adiciona os cabeçalhos em uma nova planilha."""
        try:
            requests = []
            # Prepara a criação de todas as novas abas
            for sheet_name in sheets_config.keys():
                requests.append({'addSheet': {'properties': {'title': sheet_name}}})
            
            # Adiciona a requisição para deletar a aba padrão "Página1"
            # (Assume que a nova planilha sempre tem uma 'Página1' com sheetId 0)
            requests.append({'deleteSheet': {'sheetId': 0}})

            body = {'requests': requests}
            self.sheets_service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
            st.info("Abas padrão criadas e aba inicial removida.")

            # Adiciona os cabeçalhos em cada nova aba
            for sheet_name, headers in sheets_config.items():
                self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1",
                    valueInputOption='USER_ENTERED',
                    body={'values': [headers]}
                ).execute()
            st.info("Cabeçalhos adicionados a todas as abas.")
        except Exception as e:
            st.error(f"Erro ao configurar as abas da nova planilha: {e}")
            raise

