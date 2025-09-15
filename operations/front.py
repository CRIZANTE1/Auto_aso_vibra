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
        # O ID da planilha é lido da sessão
        self.spreadsheet_id = st.session_state.get('current_spreadsheet_id')
        if not self.spreadsheet_id:
            st.error("ID da Planilha não encontrado na sessão.")
            st.stop()
            
        self.asos_data = self.load_data()
        self.data_referencia = datetime.now()

    @st.cache_data(ttl=300) # Adiciona cache para evitar recargas desnecessárias
    def load_data(_self):
        """Carrega os dados da planilha. O cache é limpo após o processamento."""
        try: # <-- O ':' FOI ADICIONADO AQUI
            # Passa o ID da planilha para a função de carregamento
            return load_asos_data(_self.spreadsheet_id)
        except Exception as e:
            st.error(f"Erro ao carregar dados da planilha: {e}")
            return {}

    def processar_todos_cpfs(self, data_inicio, data_fim):
        """
        Inicia o processo de scraping com as datas fornecidas pela interface.
        """
        try:
            with st.spinner("Buscando dados no portal RH Health... Isso pode levar alguns minutos."):
                # Passa o ID da planilha e as datas para o scraper
                scraper = RhHealthScraper(
                    spreadsheet_id=self.spreadsheet_id, 
                    data_inicio=data_inicio, 
                    data_fim=data_fim
                )
                scraper.run()
            st.success("Dados processados e atualizados com sucesso na planilha!")
            # Limpa o cache para garantir que os novos dados sejam lidos da planilha
            st.cache_data.clear()
            st.rerun()  # Força o recarregamento da página para exibir os novos dados
        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: {e}")

    def analisar_asos(self):
        st.header("🗓️ Análise de Vencimento de ASOs")

        if not self.asos_data:
            st.warning("Nenhum dado de ASO para analisar. Utilize os controles na barra lateral para processar os dados.")
            return

        # Obter os ASOs mais recentes a partir dos dados carregados
        latest_asos = get_latest_asos(self.asos_data)

        # Verificar vencimentos com base na data atual
        vencidos_monitoramento, vencidos_periodicos = check_asos_expiration(latest_asos, self.data_referencia)

        # Exibir os resultados em colunas
        col1, col2 = st.columns(2)
        with col1:
            self.exibir_vencidos("ASOs de Monitoramento Vencidos (6 meses)", vencidos_monitoramento)
        with col2:
            self.exibir_vencidos("ASOs Periódicos Vencidos (1 ano)", vencidos_periodicos)


    def exibir_vencidos(self, titulo, lista_vencidos):
        st.subheader(titulo)
        if not lista_vencidos:
            st.success(f"✔️ Nenhum ASO vencido encontrado para esta categoria.")
            return

        # Preparar dados para exibição no DataFrame
        dados_para_exibir = []
        for aso in lista_vencidos:
            dados_para_exibir.append({
                "Nome": aso.get("Nome", "N/A"),
                "Tipo de Exame": aso.get("Tipo_Exame", "N/A"),
                "Data de Realização": aso.get("Data_da_Realização", "N/A"),
                "Prestador": aso.get("Prestador", "N/A"),
            })
        
        df_vencidos = pd.DataFrame(dados_para_exibir)
        
        st.error(f"Total de vencidos: {len(df_vencidos)}")
        st.dataframe(
            df_vencidos, 
            use_container_width=True,
            hide_index=True
        )
