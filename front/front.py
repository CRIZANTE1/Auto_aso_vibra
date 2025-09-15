import streamlit as st
import json
from operations.analysis import RhHealthScraper
from operations.previsions import check_asos_expiration, load_asos_data, get_latest_asos
import pandas as pd
from datetime import datetime, date
import plotly.express as px

def page_config():
    st.set_page_config(page_title="RH Health Scraper App", page_icon=":guardsman:", layout="wide")

def run_scraper(data_inicio, data_fim):
    try:
        scraper = RhHealthScraper()
        scraper.data_inicio = data_inicio
        scraper.data_fim = data_fim
        scraper.run()
        st.success('Processamento concluído.')
    except Exception as e:
        st.error(f'Erro durante o processamento: {e}')

class initial_page:
    def __init__(self):
        with open(r'C:\Users\ce9x\Downloads\Analisys_ASO\data\funcionarios.json', encoding='utf-8') as f:
            self.funcionarios = json.load(f)
        self.cpf_list = [func["CPF"] for func in self.funcionarios]

        st.title("RH Health Scraper App")
        
        # Criando duas colunas para o layout
        col1, col2 = st.columns(2)
        
        # Coluna 1 - Lista de Funcionários
        with col1:
            st.subheader("Lista de Funcionários")
            # Criando DataFrame com nome e CPF
            df_funcionarios = pd.DataFrame(self.funcionarios)[['Nome', 'CPF']]
            st.dataframe(
                df_funcionarios,
                use_container_width=True,
                column_config={
                    "Nome": "Nome do Funcionário",
                    "CPF": "CPF"
                },
                hide_index=True,
                height=400
            )

        # Coluna 2 - ASOs Processados
        with col2:
            st.subheader("Todos os ASOs Processados")
            try:
                file_path = r'C:\Users\ce9x\Downloads\Analisys_ASO\resultados_consulta.json'
                resultados = load_asos_data(file_path)
                
                if resultados:
                    # Criando DataFrame com todos os resultados
                    todos_asos = []
                    for cpf, info in resultados.items():
                        nome = info.get('Nome', '')
                        for aso in info.get('Resultados', []):
                            aso['Nome'] = nome
                            todos_asos.append(aso)
                    
                    df_todos = pd.DataFrame(todos_asos)
                    if not df_todos.empty:
                        # Convertendo a coluna de data para datetime
                        df_todos['Data_da_Realização'] = pd.to_datetime(df_todos['Data_da_Realização'], format='%d/%m/%Y', errors='coerce')
                        df_todos = df_todos.sort_values('Data_da_Realização', ascending=False)
                        
                        # Convertendo de volta para o formato brasileiro
                        df_todos['Data_da_Realização'] = df_todos['Data_da_Realização'].dt.strftime('%d/%m/%Y')
                        
                        st.info(f"Total de ASOs encontrados: {len(df_todos)}")
                        
                        # Exibindo a tabela com todas as colunas relevantes
                        st.dataframe(
                            df_todos[["Nome", "Pedido", "Data_da_Realização", "Tipo_Exame", "Status", "Anexo_Icon"]],
                            use_container_width=True,
                            column_config={
                                "Nome": "Nome do Funcionário",
                                "Pedido": "Nº do Pedido",
                                "Data_da_Realização": "Data de Realização",
                                "Tipo_Exame": "Tipo do Exame",
                                "Status": "Status",
                                "Anexo_Icon": "Anexo"
                            },
                            hide_index=True,
                            height=400
                        )
                    else:
                        st.warning("Nenhum ASO encontrado para o período selecionado.")
            except Exception as e:
                st.error(f'Erro ao exibir resultados: {str(e)}')

        # Inicializando com a data atual
        hoje = date.today()
        
        # Usando session state para manter os valores com data padrão
        if 'data_inicio' not in st.session_state:
            st.session_state.data_inicio = hoje
        if 'data_fim' not in st.session_state:
            st.session_state.data_fim = hoje
        
        # Criando a sidebar para pesquisa
        with st.sidebar:
            st.header("Pesquisar ASOs")
            st.subheader("Selecione o período da pesquisa")
            
            data_inicio = st.date_input("Data de Início", 
                                    value=st.session_state.data_inicio,
                                    key="input_data_inicio")
            st.session_state.data_inicio = data_inicio
            
            data_fim = st.date_input("Data de Fim", 
                                    value=st.session_state.data_fim,
                                    key="input_data_fim")
            st.session_state.data_fim = data_fim

    def processar_todos_cpfs(self):
        # Calculando a diferença entre as datas
        diferenca_dias = (st.session_state.data_fim - st.session_state.data_inicio).days

        # Verificando se o intervalo é maior que 365 dias
        if diferenca_dias > 365:
            st.error("O intervalo entre as datas não pode ser maior que 365 dias!")
            return

        try:
            # Criando e configurando o scraper
            scraper = RhHealthScraper()
            scraper.data_inicio = st.session_state.data_inicio
            scraper.data_fim = st.session_state.data_fim
            
            # Executando o scraper diretamente
            with st.spinner('Processando... Por favor, aguarde.'):
                scraper.run()
                st.success('Processamento concluído com sucesso!')
                st.rerun()  # Versão atual do método para recarregar a página
        except Exception as e:
            st.error(f'Erro ao processar: {str(e)}')
            return

    def analisar_asos(self):
        try:
            st.info("Iniciando análise dos ASOS...")
            
            # Carregando os dados
            file_path = r'C:\Users\ce9x\Downloads\Analisys_ASO\resultados_consulta.json'
            resultados = load_asos_data(file_path)
            
            if not resultados:
                st.warning("Nenhum resultado encontrado para análise. Verifique se o arquivo de resultados existe.")
                return
            
            # Obtém o último ASO de monitoramento e periódico de cada funcionário
            latest_asos = get_latest_asos(resultados)

            # Verifica quais ASOs estão vencidos (usando a data atual)
            vencidos_monitoramento, vencidos_periodicos = check_asos_expiration(latest_asos)

            # Criando duas colunas para exibir os resultados
            col1, col2 = st.columns(2)

            # Coluna 1 - ASOs de Monitoramento Vencidos
            with col1:
                st.subheader("ASOs de Monitoramento Vencidos (6 meses)")
                if vencidos_monitoramento:
                    df_monitoramento = pd.DataFrame(vencidos_monitoramento)
                    st.error(f"Total: {len(vencidos_monitoramento)}")
                    st.dataframe(
                        df_monitoramento[["Nome", "Pedido", "Data_da_Realização", "Tipo_Exame", "Anexo_Icon"]],
                        use_container_width=True,
                        column_config={
                            "Nome": "Nome do Funcionário",
                            "Pedido": "Nº do Pedido",
                            "Data_da_Realização": "Data de Realização",
                            "Tipo_Exame": "Tipo do Exame",
                            "Anexo_Icon": "Anexo"
                        },
                        hide_index=True,
                        height=400
                    )
                else:
                    st.success("Nenhum ASO de monitoramento vencido.")

            # Coluna 2 - ASOs Periódicos Vencidos
            with col2:
                st.subheader("ASOs Periódicos Vencidos (1 ano)")
                if vencidos_periodicos:
                    df_periodicos = pd.DataFrame(vencidos_periodicos)
                    st.error(f"Total: {len(vencidos_periodicos)}")
                    st.dataframe(
                        df_periodicos[["Nome", "Pedido", "Data_da_Realização", "Tipo_Exame", "Anexo_Icon"]],
                        use_container_width=True,
                        column_config={
                            "Nome": "Nome do Funcionário",
                            "Pedido": "Nº do Pedido",
                            "Data_da_Realização": "Data de Realização",
                            "Tipo_Exame": "Tipo do Exame",
                            "Anexo_Icon": "Anexo"
                        },
                        hide_index=True,
                        height=400
                    )
                else:
                    st.success("Nenhum ASO periódico vencido.")

            # Gráficos
            todos_asos = []
            for cpf, info in resultados.items():
                nome = info.get('Nome', '')
                for aso in info.get('Resultados', []):
                    aso['Nome'] = nome
                    todos_asos.append(aso)
            df_todos = pd.DataFrame(todos_asos)

            # Gráfico 1: Distribuição de ASOs por Status
            st.subheader("Distribuição de ASOs por Status")
            fig_status = px.pie(df_todos, names="Status", title="Distribuição de ASOs por Status")
            st.plotly_chart(fig_status)

            # Gráfico 2: Distribuição de ASOs por Tipo de Exame
            st.subheader("Distribuição de ASOs por Tipo de Exame")
            fig_tipo_exame = px.bar(df_todos, x="Tipo_Exame", color="Status", title="Distribuição de ASOs por Tipo de Exame")
            st.plotly_chart(fig_tipo_exame)

            # Gráfico 3: Distribuição de ASOs com e sem Anexo
            st.subheader("Distribuição de ASOs com e sem Anexo")
            fig_anexo = px.histogram(df_todos, x="Anexo_Icon", color="Tipo_Exame", title="ASOs com e sem Anexo")
            st.plotly_chart(fig_anexo)

            # Gráfico 4: Distribuição de ASOs por Prestador
            st.subheader("Distribuição de ASOs por Prestador")
            fig_prestador = px.bar(df_todos, x="Prestador", color="Tipo_Exame", title="Distribuição de ASOs por Prestador")
            st.plotly_chart(fig_prestador)

            # Mensagem de conclusão
            st.success("Análise concluída com sucesso!")

        except FileNotFoundError:
            st.error("Arquivo de resultados não encontrado. Execute primeiro o processamento dos CPFs.")
        except Exception as e:
            st.error(f"Erro ao analisar ASOS: {str(e)}")
