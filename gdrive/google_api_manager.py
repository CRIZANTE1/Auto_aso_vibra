import gspread
from google.oauth2.service_account import Credentials
from gdrive.config import get_credentials_dict
import streamlit as st
import logging

logger = logging.getLogger(__name__)

class GoogleApiManager:
    def __init__(self):
        self.gc = self._get_gspread_client()

    @st.cache_resource(ttl=3600)
    def _get_gspread_client(_self):
        """Retorna um cliente gspread autenticado."""
        logger.info("CACHE MISS: Criando novo cliente gspread.")
        try:
            creds_dict = get_credentials_dict()
            creds = Credentials.from_service_account_info(
                creds_dict,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"Erro ao autenticar com o Google Sheets (gspread): {e}")
            logger.error(f"Falha ao criar cliente gspread: {e}", exc_info=True)
            return None

    def open_spreadsheet(self, spreadsheet_id: str) -> gspread.Spreadsheet | None:
        """Abre uma planilha pelo seu ID."""
        if not self.gc:
            logger.error("Não foi possível abrir a planilha pois o cliente gspread não foi inicializado.")
            return None
        try:
            logger.info(f"Abrindo planilha com ID: ...{spreadsheet_id[-6:]}")
            return self.gc.open_by_key(spreadsheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(f"Planilha com ID '{spreadsheet_id}' não encontrada.")
            return None
        except Exception as e:
            st.error(f"Ocorreu um erro ao tentar abrir a planilha: {e}")
            logger.error(f"Erro ao abrir planilha ID {spreadsheet_id}: {e}", exc_info=True)
            return None
