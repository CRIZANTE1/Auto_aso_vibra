import calendar
import json
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
from operations.sheets import SheetOperations
from gdrive.config import FUNCIONARIOS_SHEET_NAME, ASOS_SHEET_NAME

import streamlit as st

# Configure logging
logging.basicConfig(filename='scraper.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


class RhHealthScraper:

    def __init__(self, spreadsheet_id: str, data_inicio: datetime, data_fim: datetime):
        try:
            self.USERNAME = st.secrets.rhhealth.USERNAME
            self.PASSWORD = st.secrets.rhhealth.PASSWORD
            self.URL = st.secrets.rhhealth.URL
        except (AttributeError, KeyError):
            st.error("Credenciais do RH Health não encontradas nos segredos do Streamlit. Adicione a seção [rhhealth] em .streamlit/secrets.toml")
            st.stop()

        self.driver = self.setup_driver()
        self.data_inicio = data_inicio.strftime('%d/%m/%Y')
        self.data_fim = data_fim.strftime('%d/%m/%Y')
        if not spreadsheet_id:
            raise ValueError("O ID da planilha é necessário para o scraper.")
        self.sheet_ops = SheetOperations(spreadsheet_id)

    def _load_funcionarios_from_sheet(self):
        """Carrega os dados dos funcionários da planilha."""
        logging.info("Carregando funcionários da planilha...")
        df = self.sheet_ops.get_df_from_worksheet(FUNCIONARIOS_SHEET_NAME)
        if df.empty or 'CPF' not in df.columns or 'Nome' not in df.columns:
            logging.error("A aba 'funcionarios' está vazia ou não contém as colunas 'CPF' e 'Nome'.")
            return []
        # Renomeia as colunas para o formato esperado, se necessário
        df = df.rename(columns={'Nome': 'Nome', 'CPF': 'CPF'})
        return df[['Nome', 'CPF']].to_dict('records')

    def setup_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(20)
        driver.implicitly_wait(10)
        return driver

    def wait_for_element(self, xpath, timeout=20):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
        except TimeoutException as e:
            logging.error(f"Erro de timeout ao encontrar o elemento: {xpath}. Exceção: {e}")
            return None
        except Exception as e:
            logging.error(f"Erro ao encontrar o elemento: {xpath}. Exceção: {e}")
            return None

    def clear_and_set_value_with_js(self, element, value):
        try:
            self.driver.execute_script("arguments[0].setAttribute('autocomplete', 'off');", element)
            self.driver.execute_script("arguments[0].value = '';", element)
            element.send_keys(value)
        except Exception as e:
            logging.error(f"Erro ao limpar e definir valor: {e}")

    def login(self):
        try:
            self.driver.get(self.URL)
            logging.info("Página inicial carregada")

            login_field = self.wait_for_element('//input[@name="data[Usuario][apelido]"]')
            if login_field:
                self.clear_and_set_value_with_js(login_field, self.USERNAME)
                logging.info(f"Nome de usuário inserido: {self.USERNAME}")

            password_field = self.wait_for_element('//input[@name="data[Usuario][senha]"]')
            if password_field:
                self.clear_and_set_value_with_js(password_field, self.PASSWORD)
                logging.info(f"Senha inserida")

            login_button = self.wait_for_element('//button[contains(text(), "Entrar no Sistema")]')
            if login_button:
                login_button.click()
                logging.info("Botão de login clicado")

                WebDriverWait(self.driver, 30).until(EC.url_changes(self.URL))
                logging.info(f"URL após o login: {self.driver.current_url}")

                if self.driver.current_url == self.URL:
                    logging.error("Falha no login. Verifique as credenciais ou o site.")
                    return False
            return True
        except Exception as e:
            logging.error(f"Erro durante o login: {e}")
            return False

    def navigate_to_consulta(self, consulta_url):
        try:
            self.driver.get(consulta_url)
            WebDriverWait(self.driver, 30).until(EC.url_to_be(consulta_url))
            logging.info(f"Navegou para a página de consulta: {consulta_url}")
            return True
        except Exception as e:
            logging.error(f"Erro ao navegar para a página de consulta: {e}")
            return False

    def perform_search(self, cpf):
        try:
            cpf_field = self.wait_for_element('//*[@id="AgendamentoExameCpf"]')
            if cpf_field is None: return False
            cpf_field.clear()
            cpf_field.send_keys(cpf)
            logging.info(f"CPF inserido: {cpf}")

            data_inicio_field = self.wait_for_element('//*[@id="AgendamentoExameDataInicio"]')
            if data_inicio_field is None: return False
            data_inicio_field.clear()
            data_inicio_field.send_keys(self.data_inicio)
            logging.info(f"Data de início inserida: {self.data_inicio}")

            data_fim_field = self.wait_for_element('//*[@id="AgendamentoExameDataFim"]')
            if data_fim_field is None: return False
            data_fim_field.clear()
            data_fim_field.send_keys(self.data_fim)
            logging.info(f"Data de fim inserida: {self.data_fim}")

            buscar_button = self.wait_for_element('//*[@id="AgendamentoExameIndexForm"]/input')
            if buscar_button is None: return False
            buscar_button.click()
            logging.info("Botão 'Buscar' clicado")

            WebDriverWait(self.driver, 30).until(
                EC.invisibility_of_element_located((By.ID, "loading-indicator"))
            )
            logging.info("A busca foi realizada")

            no_results = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'Nenhum registro encontrado')]")
            if no_results:
                logging.info(f"Nenhum resultado encontrado para o CPF: {cpf}")
                return False
            return True
        except Exception as e:
            logging.error(f"Erro ao realizar a busca: {e}")
            return False

    def process_results(self):
        try:
            logging.info("Iniciando o processamento dos resultados")
            tabela = self.wait_for_element("//table[contains(@class, 'table-striped')]")
            if tabela is None: return []
            linhas = tabela.find_elements(By.TAG_NAME, "tr")
            logging.info(f"Número de linhas encontradas: {len(linhas)}")

            resultados = []
            for linha in linhas[1:]:  # Pula o cabeçalho
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) >= 12:
                    anexo_icon = False
                    try:
                        anexo_element = colunas[0].find_element(By.CSS_SELECTOR, '.icon-file')
                        if 'btn-anexos visualiza_anexo' in anexo_element.get_attribute('class'):
                            anexo_icon = True
                    except NoSuchElementException:
                        pass

                    resultado = {
                        "Anexo_Icon": "Com anexo" if anexo_icon else "Sem anexo",
                        "Pedido": colunas[1].text.strip(),
                        "Responsavel": colunas[2].text.strip(),
                        "local": colunas[3].text.strip(),
                        "Nome": colunas[4].text.strip(),
                        "Prestador": colunas[5].text.strip(),
                        "Tipo_Exame": colunas[6].text.strip(),
                        "Exame": colunas[7].text.strip(),
                        "Data_Emissão": colunas[8].text.strip(),
                        "Agendamento": colunas[9].text.strip(),
                        "Status": colunas[10].text.strip(),
                        "Data_da_Realização": colunas[11].text.strip(),
                    }
                    resultados.append(resultado)
            return resultados
        except Exception as e:
            logging.error(f"Erro ao processar os resultados: {e}")
            return []

    def _save_results_to_sheet(self, todos_resultados):
        """Salva os resultados consolidados na planilha."""
        logging.info("Salvando resultados na planilha...")
        try:
            # Transforma o dicionário de resultados em uma lista de linhas para o DataFrame
            data_to_save = []
            for cpf, data in todos_resultados.items():
                for resultado in data['Resultados']:
                    row = {
                        'CPF': cpf,
                        'Nome_Funcionario': data['Nome'],
                        **resultado # Adiciona todos os campos do resultado
                    }
                    data_to_save.append(row)
            
            if not data_to_save:
                logging.info("Nenhum resultado para salvar na planilha.")
                return

            df = pd.DataFrame(data_to_save)
            
            # Garante a ordem das colunas
            header = ['CPF', 'Nome_Funcionario', 'Anexo_Icon', 'Pedido', 'Responsavel', 'local', 'Nome', 'Prestador', 'Tipo_Exame', 'Exame', 'Data_Emissão', 'Agendamento', 'Status', 'Data_da_Realização']
            df = df[header]

            # Limpa a aba antes de inserir novos dados
            worksheet = self.sheet_ops._get_worksheet(ASOS_SHEET_NAME)
            if not worksheet:
                logging.error(f"Aba {ASOS_SHEET_NAME} não encontrada. Não foi possível salvar os resultados.")
                return
                
            worksheet.clear()
            
            # Converte o DataFrame para lista de listas (cabeçalho + dados)
            data_list = [df.columns.values.tolist()] + df.values.tolist()
            
            # Usa gspread para inserir os dados
            worksheet.update(data_list, value_input_option='USER_ENTERED')

            logging.info(f"{len(df)} linhas de resultados salvas na aba '{ASOS_SHEET_NAME}'.")

        except Exception as e:
            logging.error(f"Erro ao salvar os resultados na planilha: {e}", exc_info=True)
            raise

    def run(self):
        funcionarios = self._load_funcionarios_from_sheet()
        if not funcionarios:
            logging.warning("Nenhum funcionário carregado. O scraper não será executado.")
            return
            
        todos_resultados = {}

        try:
            if self.login():
                for funcionario in funcionarios:
                    nome = funcionario["Nome"]
                    cpf = funcionario["CPF"]
                    logging.info(f"Processando funcionário: {nome} (CPF: {cpf})")
                    
                    if self.navigate_to_consulta("https://portal.rhhealth.com.br/portal/consultas_agendas"):
                        if self.perform_search(cpf):
                            resultados = self.process_results()
                            todos_resultados[cpf] = {"Nome": nome, "Resultados": resultados}
                        else:
                            todos_resultados[cpf] = {"Nome": nome, "Resultados": []}
                    
                    logging.info(f"Processamento concluído para o funcionário: {nome}")

                self._save_results_to_sheet(todos_resultados)
            else:
                raise Exception("Falha no login")
        finally:
            self.driver.quit()

