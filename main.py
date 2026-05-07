import streamlit as st
import pdfplumber
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Orçamentador de Estruturas", layout="wide")

st.title("🏗️ Orçamentador Inteligente de Aço")
st.write("Suba o PDF do projeto para extrair a relação de aço e gerar o orçamento.")

# 1. Configurações do Usuário
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", min_value=0.0, value=8.50)
with col2:
    porcentagem_mo = st.number_input("Margem de Mão de Obra (%)", min_value=0.0, value=20.0) / 100

# 2. Upload do Ficheiro
uploaded_file = st.file_uploader("Escolha o arquivo PDF (Planta Estrutural)", type="pdf")

if uploaded_file is not None:
    dados_extraidos = []
    
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            # Tenta extrair tabelas da página
            tabelas = page.extract_table()
            if tabelas:
                for linha in tabelas:
                    # Filtra linhas que pareçam ser de aço (ex: que contenham bitolas)
                    # Aqui adaptamos conforme o padrão das tuas pranchas [cite: 75, 77]
                    if linha[0] and any(x in str(linha[0]) for x in ['5.0', '6.3', '8.0', '10.0', '12.5']):
                        dados_extraidos.append(linha)

    if dados_extraidos:
        # Criar DataFrame para organizar os dados
        df = pd.DataFrame(dados_extraidos)
        st.subheader("Dados Identificados no Projeto")
        st.dataframe(df)
        
        # Exemplo de lógica de cálculo simplificada
        # (Nota: A lógica exata depende de qual coluna do seu PDF é o peso/comprimento)
        st.success("Tabela de aço processada com sucesso!")
        
        # Botão para gerar o orçamento final
        if st.button("Gerar Orçamento Desmembrado"):
            st.write("### Resumo do Orçamento")
            # Aqui entraria a soma total baseada no processamento do PDF
            st.info("Funcionalidade: O código calcularia o peso total e somaria sua margem de mão de obra.")
    else:
        st.warning("Não foi possível detectar uma tabela de aço clara. Verifique o formato do PDF.")
