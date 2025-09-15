# Projeto de Análise de ASO

## Descrição

Esta é uma aplicação web desenvolvida com Streamlit para automatizar a análise de vencimento de Atestados de Saúde Ocupacional (ASO). O sistema realiza a extração de dados do portal RH Health, armazena as informações em planilhas do Google Sheets e apresenta uma análise dos ASOs próximos do vencimento.

A aplicação conta com autenticação de usuários via Google, suporte a múltiplas unidades operacionais e uma interface simples para visualização e processamento dos dados.

## Funcionalidades

- **Autenticação Segura:** Login de usuários utilizando contas Google (OIDC).
- **Gerenciamento Multi-unidade:** O sistema permite cadastrar diferentes unidades operacionais, cada uma com sua própria planilha de dados.
- **Extração Automatizada de Dados:** Um scraper (Selenium) busca os dados de ASOs diretamente do portal RH Health.
- **Armazenamento Centralizado:** Todas as informações, incluindo permissões de usuários, configurações de unidades e dados de ASOs, são armazenadas no Google Sheets.
- **Análise de Vencimentos:** A interface principal exibe de forma clara os ASOs de monitoramento (vencimento em 6 meses) and periódicos (vencimento em 1 ano) que já venceram.

## Configuração do Ambiente

Siga os passos abaixo para configurar e executar o projeto.

### 1. Pré-requisitos

- Python 3.9+ (recomendado)
- Google Chrome instalado (para o Selenium)
- Uma conta Google Cloud

### 2. Instalação

Clone o repositório e instale as dependências:

```bash
pip install -r requirements.txt
```

### 3. Configuração do Google Cloud

1.  **Crie um Projeto:** Acesse o [console do Google Cloud](https://console.cloud.google.com/) e crie um novo projeto.
2.  **Ative as APIs:** No seu projeto, ative a **Google Drive API** e a **Google Sheets API**.
3.  **Crie uma Conta de Serviço:**
    - Vá para "IAM e Admin" > "Contas de Serviço".
    - Crie uma nova conta de serviço.
    - Gere uma chave para esta conta no formato JSON e faça o download.
4.  **Compartilhe as Planilhas:** Compartilhe as planilhas do Google (Matriz e das unidades) com o e-mail da conta de serviço que você criou.

### 4. Configuração do Streamlit (secrets.toml)

Crie um arquivo `.streamlit/secrets.toml` na raiz do projeto para armazenar as credenciais de forma segura.

**Credenciais do Google Sheets:**

Adicione as informações do arquivo JSON da sua conta de serviço.

```toml
[connections.gsheets]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

**Credenciais de Autenticação (OIDC):**

Configure as credenciais do OAuth 2.0 para o login com Google.

```toml
[oidc]
google_client_id = "SEU_CLIENT_ID_DO_GOOGLE.apps.googleusercontent.com"
google_client_secret = "SEU_CLIENT_SECRET_DO_GOOGLE"
google_discovery_url = "https://accounts.google.com"
```

### 5. Configuração das Planilhas Google

1.  **Planilha Matriz:**
    - Crie uma planilha para ser a "Matriz" do sistema.
    - Adicione o ID desta planilha na variável `MATRIX_SHEETS_ID` no arquivo `gdrive/config.py`.
    - Crie as seguintes abas nesta planilha:
        - `adm`: Com as colunas `email`, `nome`, `role` (`admin`, `editor`, `viewer`), `unidade_operacional`.
        - `unidades`: Com as colunas `nome_unidade`, `spreadsheet_id`, `folder_id`.

2.  **Planilhas das Unidades:**
    - Para cada unidade cadastrada na Planilha Matriz, crie uma planilha separada.
    - O ID de cada uma deve ser informado na coluna `spreadsheet_id` da aba `unidades` na Planilha Matriz.
    - Cada planilha de unidade deve conter as seguintes abas:
        - `funcionarios`: Com as colunas `CPF` e `Nome`.
        - `asos`: Esta aba será preenchida automaticamente pelo scraper. O cabeçalho esperado é: `CPF`, `Nome_Funcionario`, `Anexo_Icon`, `Pedido`, `Responsavel`, `local`, `Nome`, `Prestador`, `Tipo_Exame`, `Exame`, `Data_Emissão`, `Agendamento`, `Status`, `Data_da_Realização`.

## Como Usar

1.  **Execute a Aplicação:**

    ```bash
    streamlit run main.py
    ```

2.  **Login:** Acesse a URL fornecida pelo Streamlit e faça login com sua conta Google.

3.  **Seleção de Unidade:** Na interface, selecione a Unidade Operacional que deseja analisar.

4.  **Processar Dados:** Clique no botão "Processar ASOs" na barra lateral. O scraper será iniciado para buscar os dados mais recentes. Aguarde a conclusão.

5.  **Analisar Resultados:** Após o processamento, a página será atualizada e exibirá as tabelas com os ASOs vencidos.

## Estrutura do Projeto

```
.
├── auth/                # Módulos de autenticação e permissões
├── data/                # (Obsoleto, pode ser removido)
├── gdrive/              # Módulos para interação com a API do Google
├── operations/          # Lógica de negócio (scraper, frontend, análises)
├── .streamlit/          # Pasta para configuração do Streamlit
│   └── secrets.toml     # Arquivo de credenciais
├── main.py              # Ponto de entrada da aplicação
├── requirements.txt     # Dependências do Python
└── README.md            # Este arquivo
```
