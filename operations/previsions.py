import json
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from operations.sheets import SheetOperations
from gdrive.config import ASOS_SHEET_NAME

def get_latest_asos(asos_data):
    """
    Retorna um dicionário contendo o ASO mais recente de cada tipo 
    (monitoramento e periódico) para cada funcionário.
    """
    latest_asos = {}

    for cpf, info in asos_data.items():
        resultados = info.get('Resultados', [])
        latest_monitoramento = None
        latest_periodico = None

        for aso in resultados:
            tipo_exame = aso.get("Tipo_Exame", "").strip().upper()
            data_realizacao_str = aso.get("Data_da_Realização", "").strip()

            if not data_realizacao_str:  # Ignora ASOs sem data
                continue

            try:
                data_realizacao = datetime.strptime(data_realizacao_str, '%d/%m/%Y')

                # Verifica se é um ASO de monitoramento
                if "MONITORAÇÃO PONTUAL" in tipo_exame:
                    if latest_monitoramento is None or data_realizacao > datetime.strptime(latest_monitoramento["Data_da_Realização"], '%d/%m/%Y'):
                        latest_monitoramento = aso

                # Verifica se é um ASO periódico
                elif "EXAME PERIÓDICO" in tipo_exame:
                    if latest_periodico is None or data_realizacao > datetime.strptime(latest_periodico["Data_da_Realização"], '%d/%m/%Y'):
                        latest_periodico = aso

            except ValueError:
                continue  # Ignora erros de formato de data

        # Armazena o ASO mais recente de cada tipo
        if latest_monitoramento:
            latest_monitoramento['Nome'] = info.get('Nome', '')
            latest_asos.setdefault(cpf, {})['monitoramento'] = latest_monitoramento
        if latest_periodico:
            latest_periodico['Nome'] = info.get('Nome', '')
            latest_asos.setdefault(cpf, {})['periodico'] = latest_periodico

    return latest_asos


def check_asos_expiration(asos_data, data_referencia=None):
    """
    Verifica o vencimento dos ASOs de monitoramento e periódicos.
    Usa a data atual (datetime.now()) como padrão, mas permite passar uma data de referência personalizada.
    """
    vencidos_monitoramento = []
    vencidos_periodicos = []

    # Define a data de referência
    if data_referencia is None:
        data_referencia = datetime.now()  # Usa a data e hora atuais como padrão

    for cpf, asos in asos_data.items():
        if 'monitoramento' in asos:
            try:
                data_realizacao_str = asos['monitoramento'].get("Data_da_Realização", "").strip()
                if not data_realizacao_str:
                    continue  # Ignora ASOs sem data de realização

                data_realizacao = datetime.strptime(data_realizacao_str, '%d/%m/%Y')
                data_vencimento = data_realizacao + timedelta(days=180)  # 6 meses
                if data_vencimento < data_referencia:
                    vencidos_monitoramento.append(asos['monitoramento'])
            except (ValueError, KeyError) as e:
                print(f"Erro ao calcular vencimento do ASO de monitoramento para {asos.get('Nome', 'Nome não disponível')} (CPF: {cpf}): {e}")

        if 'periodico' in asos:
            try:
                data_realizacao_str = asos['periodico'].get("Data_da_Realização", "").strip()
                if not data_realizacao_str:
                    continue  # Ignora ASOs sem data de realização

                data_realizacao = datetime.strptime(data_realizacao_str, '%d/%m/%Y')
                data_vencimento = data_realizacao + timedelta(days=365)  # 1 ano
                if data_vencimento < data_referencia:
                    vencidos_periodicos.append(asos['periodico'])
            except (ValueError, KeyError) as e:
                print(f"Erro ao calcular vencimento do ASO periódico para {asos.get('Nome', 'Nome não disponível')} (CPF: {cpf}): {e}")

    return vencidos_monitoramento, vencidos_periodicos


def check_duplicates(asos_data):
    duplicates = defaultdict(list)
    for cpf, info in asos_data.items():
        resultados = info.get('Resultados', [])
        for aso in resultados:
            if "monitor" in aso.get("Tipo_Exame", "").lower():
                key = (cpf, aso["Data_da_Realização"])
                duplicates[key].append(aso)
    
    for key, asos in duplicates.items():
        if len(asos) > 1:
            print(f"Duplicação encontrada para CPF {key[0]} na data {key[1]}: {len(asos)} ASOs")

def load_asos_data(spreadsheet_id: str):
    """Carrega os dados dos ASOs a partir da planilha e os transforma na estrutura aninhada esperada."""
    try:
        sheet_ops = SheetOperations(spreadsheet_id)
        df = sheet_ops.get_df_from_worksheet(ASOS_SHEET_NAME)
        
        if df.empty:
            return {}

        # Renomeia a coluna 'Nome_Funcionario' para 'Nome' para consistência interna
        if 'Nome_Funcionario' in df.columns:
            df = df.rename(columns={'Nome_Funcionario': 'Nome'})

        todos_resultados = {}
        for cpf, group in df.groupby('CPF'):
            # O nome do funcionário deve ser o mesmo para todo o grupo
            nome_funcionario = group['Nome'].iloc[0]
            
            # Converte o grupo de volta para uma lista de dicionários
            resultados = group.to_dict('records')
            
            todos_resultados[cpf] = {
                "Nome": nome_funcionario,
                "Resultados": resultados
            }
            
        return todos_resultados

    except FileNotFoundError:
        raise FileNotFoundError("Arquivo de resultados não encontrado")
    except json.JSONDecodeError:
        raise ValueError("Erro ao decodificar o arquivo JSON")
    except Exception as e:
        raise Exception(f"Erro ao carregar dados: {str(e)}")

