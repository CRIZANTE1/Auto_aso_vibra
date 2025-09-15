
import logging
import sys
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
from operations.sheets import SheetOperations
from gdrive.config import FUNCIONARIOS_SHEET_NAME, ASOS_SHEET_NAME
import streamlit as st

# Configuração de logging para exibir mensagens no terminal e em um arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [SCRAPER] - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler(sys.stdout)  # Envia logs para o terminal
    ]
)

class RhHealthScraper:
    def __init__(self, spreadsheet_id: str, data_inicio: datetime, data_fim: datetime):
        try:
            self.USERNAME = st.secrets.rhhealth.USERNAME
            self.PASSWORD = st.secrets.rhhealth.PASSWORD
            self.URL = st.secrets.rhhealth.URL
        except (AttributeError, KeyError):
            st.error("Credenciais do RH Health não encontradas. Verifique a seção [rhhealth] em .streamlit/secrets.toml")
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
            st.warning("A aba 'funcionarios' da sua planilha está vazia ou não possui as colunas 'CPF' e 'Nome'.")
            return []
        
        logging.info(f"Encontrados {len(df)} funcionários para processar.")
        df = df.rename(columns={'Nome': 'Nome', 'CPF': 'CPF'})
        return df[['Nome', 'CPF']].to_dict('records')

    def setup_driver(self):
        logging.info("Configurando o driver do Selenium (Headless Chrome)...")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(15)
        logging.info("Driver configurado.")
        return driver

    def wait_for_element(self, xpath, timeout=20):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, xpath))
            )
        except TimeoutException:
            logging.error(f"Elemento não encontrado (timeout): {xpath}.")
            return None
        except Exception as e:
            logging.error(f"Erro ao encontrar o elemento: {xpath}. Exceção: {e}")
            return None

    def login(self):
        try:
            logging.info(f"Acessando a URL de login: {self.URL}")
            self.driver.get(self.URL)

            login_field = self.wait_for_element('//input[@name="data[Usuario][apelido]"]')
            if not login_field:
                logging.error("Campo de login não encontrado.")
                return False
            login_field.send_keys(self.USERNAME)
            logging.info("Nome de usuário inserido.")

            password_field = self.wait_for_element('//input[@name="data[Usuario][senha]"]')
            if not password_field:
                logging.error("Campo de senha não encontrado.")
                return False
            password_field.send_keys(self.PASSWORD)
            logging.info("Senha inserida.")

            # --- CORREÇÃO IMPORTANTE AQUI ---
            # O botão agora é apenas "Entrar"
            login_button = self.wait_for_element('//button[contains(text(), "Entrar")]')
            # --- FIM DA CORREÇÃO ---
            
            if not login_button:
                logging.error("Botão de login não encontrado. O texto pode ter mudado novamente.")
                self.driver.save_screenshot('debug_login_error.png')
                logging.info("Screenshot 'debug_login_error.png' salvo para análise.")
                return False
                
            login_button.click()
            logging.info("Botão de login clicado. Aguardando redirecionamento...")

            WebDriverWait(self.driver, 30).until(EC.url_contains("painel"))
            logging.info(f"Login bem-sucedido! URL atual: {self.driver.current_url}")
            return True

        except Exception as e:
            logging.error(f"Ocorreu uma exceção grave durante o login: {e}")
            self.driver.save_screenshot('debug_login_exception.png')
            logging.info("Screenshot 'debug_login_exception.png' salvo.")
            return False

    def navigate_to_consulta(self, consulta_url):
        try:
            logging.info(f"Navegando para a página de consulta: {consulta_url}")
            self.driver.get(consulta_url)
            WebDriverWait(self.driver, 30).until(EC.url_to_be(consulta_url))
            logging.info("Página de consulta carregada.")
            return True
        except Exception as e:
            logging.error(f"Erro ao navegar para a página de consulta: {e}")
            return False

    def perform_search(self, cpf):
        try:
            cpf_field = self.wait_for_element('//*[@id="AgendamentoExameCpf"]')
            if not cpf_field: return False
            cpf_field.clear()
            cpf_field.send_keys(cpf)
            logging.info(f"CPF inserido na busca: {cpf}")

            data_inicio_field = self.wait_for_element('//*[@id="AgendamentoExameDataInicio"]')
            if not data_inicio_field: return False
            data_inicio_field.clear()
            data_inicio_field.send_keys(self.data_inicio)

            data_fim_field = self.wait_for_element('//*[@id="AgendamentoExameDataFim"]')
            if not data_fim_field: return False
            data_fim_field.clear()
            data_fim_field.send_keys(self.data_fim)
            logging.info(f"Período de busca: {self.data_inicio} a {self.data_fim}")

            buscar_button = self.wait_for_element('//*[@id="AgendamentoExameIndexForm"]/input')
            if not buscar_button: return False
            buscar_button.click()
            logging.info("Botão 'Buscar' clicado. Aguardando resultados...")
            
            WebDriverWait(self.driver, 30).until(EC.invisibility_of_element_located((By.ID, "loading-indicator")))

            try:
                self.driver.find_element(By.XPATH, "//div[contains(text(), 'Nenhum registro encontrado')]")
                logging.warning(f"Nenhum resultado encontrado para o CPF: {cpf} no período.")
                return False
            except NoSuchElementException:
                logging.info(f"Tabela de resultados encontrada para o CPF: {cpf}.")
                return True

        except Exception as e:
            logging.error(f"Erro ao realizar a busca: {e}")
            return False

    def process_results(self):
        try:
            logging.info("Processando a tabela de resultados...")
            tabela = self.wait_for_element("//table[contains(@class, 'table-striped')]")
            if not tabela: 
                logging.error("Tabela de resultados não encontrada na página.")
                return []
            
            linhas = tabela.find_elements(By.TAG_NAME, "tr")
            if len(linhas) <= 1:
                logging.warning("Tabela encontrada, mas sem linhas de dados.")
                return []
            
            logging.info(f"Encontradas {len(linhas) - 1} linhas de dados.")
            resultados = []
            for linha in linhas[1:]:
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) >= 12:
                    anexo_icon = "Sem anexo"
                    try:
                        colunas[0].find_element(By.CSS_SELECTOR, '.icon-file')
                        anexo_icon = "Com anexo"
                    except NoSuchElementException:
                        pass

                    resultado = {
                        "Anexo_Icon": anexo_icon,
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
            logging.error(f"Erro ao processar os resultados da tabela: {e}")
            return []

    def _save_results_to_sheet(self, todos_resultados):
        if not todos_resultados:
            logging.warning("Nenhum resultado foi coletado para salvar na planilha.")
            return

        logging.info("Preparando para salvar resultados na planilha...")
        try:
            data_to_save = []
            for cpf, data in todos_resultados.items():
                for resultado in data.get('Resultados', []):
                    row = {'CPF': cpf, 'Nome_Funcionario': data['Nome'], **resultado}
                    data_to_save.append(row)
            
            header = ['CPF', 'Nome_Funcionario', 'Anexo_Icon', 'Pedido', 'Responsavel', 'local', 'Nome', 'Prestador', 'Tipo_Exame', 'Exame', 'Data_Emissão', 'Agendamento', 'Status', 'Data_da_Realização']
            worksheet = self.sheet_ops._get_worksheet(ASOS_SHEET_NAME)
            
            if not worksheet:
                logging.error(f"Aba '{ASOS_SHEET_NAME}' não encontrada. Não foi possível salvar.")
                st.error(f"Aba '{ASOS_SHEET_NAME}' não encontrada na planilha. Crie-a para salvar os resultados.")
                return
            
            worksheet.clear()
            logging.info(f"Aba '{ASOS_SHEET_NAME}' limpa.")
            
            if not data_to_save:
                logging.info("Nenhum registro de ASO encontrado para salvar. Apenas o cabeçalho será escrito.")
                worksheet.update([header], value_input_option='USER_ENTERED')
                return

            df = pd.DataFrame(data_to_save)
            df = df.reindex(columns=header) # Garante a ordem correta
            data_list = [df.columns.values.tolist()] + df.values.tolist()
            
            logging.info(f"Enviando {len(df)} linhas para a planilha...")
            worksheet.update(data_list, value_input_option='USER_ENTERED')
            logging.info(f"Resultados salvos com sucesso na aba '{ASOS_SHEET_NAME}'.")

        except Exception as e:
            logging.error(f"Erro ao salvar os resultados na planilha: {e}", exc_info=True)
            st.error(f"Falha ao salvar dados na planilha: {e}")
            raise

    def run(self):
        funcionarios = self._load_funcionarios_from_sheet()
        if not funcionarios:
            logging.warning("Nenhum funcionário para processar. Encerrando execução.")
            return
            
        todos_resultados = {}
        try:
            if self.login():
                for funcionario in funcionarios:
                    nome = funcionario["Nome"]
                    cpf = funcionario["CPF"]
                    logging.info(f"--- Processando funcionário: {nome} (CPF: {cpf}) ---")
                    
                    if self.navigate_to_consulta("https://portal.rhhealth.com.br/portal/consultas_agendas"):
                        if self.perform_search(cpf):
                            resultados = self.process_results()
                            todos_resultados[cpf] = {"Nome": nome, "Resultados": resultados}
                        else:
                            todos_resultados[cpf] = {"Nome": nome, "Resultados": []}
                    else:
                        logging.error(f"Falha ao navegar para a página de consulta para o funcionário {nome}.")
                    
                    logging.info(f"--- Fim do processamento para: {nome} ---")

                self._save_results_to_sheet(todos_resultados)
            else:
                st.error("Falha no login no portal RH Health. Verifique as credenciais em `secrets.toml` e se o site está acessível.")
                raise Exception("Falha no login")
        finally:
            logging.info("Encerrando o driver do Selenium.")
            self.driver.quit()

