import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="Orçamentador Parceiro", layout="wide")
st.title("🏗️ Orçamentador de Ferragens (Versão 2.0)")

# Configurações de Preço
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.0)
with col2:
    margem_mo = st.number_input("Margem Mão de Obra (%)", value=20.0) / 100

u_file = st.file_uploader("Suba a planta (PDF)", type="pdf")

if u_file:
    dados_extraidos = []
    
    with pdfplumber.open(u_file) as pdf:
        for page in pdf.pages:
            # Extrai o texto bruto da página para análise
            texto = page.extract_text()
            if not texto:
                continue
            
            # Procura por padrões comuns em tabelas de aço (Ex: 10.0  42.5  kg)
            # Esta expressão regular procura: Bitola -> Espaçamento -> Peso
            linhas = texto.split('\n')
            for linha in linhas:
                # Procura bitolas conhecidas na linha
                if any(b in linha for b in ['5,0', '6,3', '8,0', '10,0', '12,5', '16,0']):
                    # Tenta encontrar números que pareçam PESO (ex: 12,50 ou 120.5)
                    numeros = re.findall(r'\d+[\.,]\d+', linha)
                    if len(numeros) >= 2:
                        bitola = numeros[0]
                        peso = float(numeros[-1].replace(',', '.')) # Assume que o último número da linha é o peso total
                        
                        custo_mat = peso * preco_kg
                        custo_mo = custo_mat * margem_mo
                        
                        dados_extraidos.append({
                            "Bitola (mm)": bitola,
                            "Peso Lido (kg)": peso,
                            "Material (R$)": round(custo_mat, 2),
                            "Mão de Obra (R$)": round(custo_mo, 2),
                            "Total Item (R$)": round(custo_mat + custo_mo, 2)
                        })

    if dados_extraidos:
        df = pd.DataFrame(dados_extraidos).drop_duplicates()
        st.write("### Itens Detectados:")
        st.table(df)
        
        total_geral = df['Total Item (R$)'].sum()
        st.success(f"💰 VALOR TOTAL DO ORÇAMENTO: R$ {total_geral:,.2f}")
    else:
        st.error("Não consegui extrair dados automáticos.")
        st.info("Dica: Se o PDF for uma foto/imagem, o computador não consegue ler o texto. O PDF precisa ser 'selecionável'.")
