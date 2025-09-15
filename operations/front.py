import streamlit as st
import pandas as pd
from datetime import datetime
from operations.previsions import get_latest_asos, check_asos_expiration, load_asos_data
from operations.analysis import RhHealthScraper


def page_config():
    st.set_page_config(
        page_title="Análise de ASO",
        page_icon="✅",
        layout="wide",
        initial_sidebar_state="expanded"
    )

class initial_page:
    def __init__(self):
        # O ID da planilha agora é necessário na inicialização
        self.spreadsheet_id = st.session_state.get('current_spreadsheet_id')
        if not self.spreadsheet_id:
            st.error("ID da Planilha não encontrado na sessão. Selecione uma unidade.")
            st.stop()
            
        self.asos_data = self.load_data()
        self.data_referencia = datetime.now()

    def load_data(self):
        try:
            # Passa o ID da planilha para a função de carregamento
            return load_asos_data(self.spreadsheet_id)
        except Exception as e:
            st.error(f"Erro ao carregar dados da planilha: {e}")
            return {}

    def processar_todos_cpfs(self):
        # O botão foi movido para a sidebar no main.py, esta função é chamada por ele
        try:
            with st.spinner("Buscando dados... Isso pode levar alguns minutos."):
                # Passa o ID da planilha para o scraper
                scraper = RhHealthScraper(spreadsheet_id=self.spreadsheet_id)
                scraper.run()
            st.success("Dados processados e atualizados com sucesso na planilha!")
            # Limpa o cache para garantir que os novos dados sejam lidos
            st.cache_data.clear()
            st.rerun()  # Força o recarregamento da página para exibir os novos dados
        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: {e}")

    def analisar_asos(self):
        st.header("🗓️ Análise de Vencimento de ASOs")

        if not self.asos_data:
            st.warning("Nenhum dado de ASO para analisar. Processe os dados primeiro.")
            return

        # Obter os ASOs mais recentes
        latest_asos = get_latest_asos(self.asos_data)

        # Verificar vencimentos
        vencidos_monitoramento, vencidos_periodicos = check_asos_expiration(latest_asos, self.data_referencia)

        # Exibir resultados
        self.exibir_vencidos("ASOs de Monitoramento Vencidos (6 meses)", vencidos_monitoramento)
        self.exibir_vencidos("ASOs Periódicos Vencidos (1 ano)", vencidos_periodicos)

    def exibir_vencidos(self, titulo, lista_vencidos):
        st.subheader(titulo)
        if not lista_vencidos:
            st.success("Nenhum ASO vencido encontrado.")
            return

        # Preparar dados para o DataFrame
        dados_vencidos = []
        for aso in lista_vencidos:
            dados_vencidos.append({
                "Nome": aso.get("Nome", "N/A"),
                "Tipo de Exame": aso.get("Tipo_Exame", "N/A"),
                "Data de Realização": aso.get("Data_da_Realização", "N/A"),
                "Prestador": aso.get("Prestador", "N/A"),
            })

        df_vencidos = pd.DataFrame(dados_vencidos)
        st.dataframe(df_vencidos, height=300, width=1000)
