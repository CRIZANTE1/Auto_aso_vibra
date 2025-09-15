from operations.front import initial_page, page_config
import streamlit as st

def main():
    page_config()
    page = initial_page()
    
    # Criando a sidebar para pesquisa
    with st.sidebar:
        # Botão de processamento na sidebar com chave única
        if st.button("Processar ASOs", key="btn_processar_sidebar"):
            page.processar_todos_cpfs()
    
    page.analisar_asos()

if __name__ == "__main__":
    main()
