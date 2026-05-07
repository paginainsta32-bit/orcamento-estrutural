import streamlit as st
import google.generativeai as genai
import PIL.Image
import pdf2image
import pandas as pd
import io

# 1. Configuração da IA (Coloque sua chave aqui ou use segredos do Streamlit)
st.sidebar.title("Configuração")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🏗️ Orçamentador com IA Visionária")
st.write("Esta versão 'enxerga' o projeto como um humano faria.")

# Configurações de Preço
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.0)
with col2:
    margem_mo = st.number_input("Mão de Obra (%)", value=20.0) / 100

u_file = st.file_uploader("Suba a planta (PDF ou Imagem)", type=["pdf", "png", "jpg"])

if u_file and api_key:
    # Converter PDF para Imagem para a IA "olhar"
    if u_file.type == "application/pdf":
        images = pdf2image.convert_from_bytes(u_file.read())
        img = images[0] # Pega a primeira página (geralmente onde está o resumo)
    else:
        img = PIL.Image.open(u_file)

    st.image(img, caption="Projeto Carregado", use_column_width=True)

    if st.button("Analisar com IA"):
        with st.spinner("A IA está lendo a tabela de aço..."):
            prompt = """
            Analise esta prancha estrutural. Localize a tabela de 'RESUMO DO AÇO'.
            Extraia as bitolas e o PESO TOTAL de cada uma (incluindo os 10% se houver).
            Retorne APENAS uma lista no formato: Bitola | Peso
            Exemplo:
            10.0 | 150.5
            5.0 | 40.2
            """
            
            response = model.generate_content([prompt, img])
            
            # Processar resposta da IA
            linhas = response.text.strip().split('\n')
            dados = []
            for l in linhas:
                if '|' in l:
                    b, p = l.split('|')
                    peso_val = float(p.replace(',', '.').strip())
                    custo_mat = peso_val * preco_kg
                    dados.append({
                        "Bitola": b.strip(),
                        "Peso (kg)": peso_val,
                        "Material": custo_mat,
                        "Mão de Obra": custo_mat * margem_mo,
                        "Total": custo_mat * (1 + margem_mo)
                    })
            
            if dados:
                df = pd.DataFrame(dados)
                st.table(df)
                st.success(f"Total: R$ {df['Total'].sum():.2f}")
