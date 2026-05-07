import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Inteligente", layout="wide")

# Interface Lateral
st.sidebar.title("Configuração")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

st.title("🏗️ Orçamentador de Ferragens com IA")
st.info("Esta versão utiliza visão computacional para ler tabelas complexas de projetos.")

# Configurações de Negócio
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.0)
with col2:
    margem_mo = st.number_input("Mão de Obra (%)", value=20.0) / 100

u_file = st.file_uploader("Suba a planta (PDF)", type=["pdf"])

if u_file and api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Abrir PDF com PyMuPDF
    doc = fitz.open(stream=u_file.read(), filetype="pdf")
    
    # Vamos processar a primeira página (onde geralmente estão as tabelas)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Aumenta a resolução para a IA ler melhor
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    st.image(img, caption="Visualização do Projeto", use_column_width=True)

    if st.button("Analisar Projeto e Gerar Orçamento"):
        with st.spinner("A IA está analisando a tabela de resumo de aço..."):
            # Prompt específico para o seu tipo de planta
            prompt = """
            Localize a tabela 'RESUMO DO AÇO' nesta planta.
            Extraia o peso total para cada bitola (Ø). 
            Ignore textos informativos e foque nos dados numéricos de peso.
            Retorne os dados exatamente neste formato, um por linha:
            Bitola | Peso
            Exemplo:
            5.0 | 25.4
            10.0 | 110.0
            """
            
            response = model.generate_content([prompt, img])
            
            # Processamento dos resultados
            dados = []
            for linha in response.text.strip().split('\n'):
                if '|' in linha:
                    try:
                        partes = linha.split('|')
                        bitola = partes[0].strip()
                        # Limpa o peso de unidades como 'kg' e converte vírgula em ponto
                        peso_str = partes[1].lower().replace('kg', '').replace(',', '.').strip()
                        peso_val = float(peso_str)
                        
                        custo_mat = peso_val * preco_kg
                        custo_mo = custo_mat * margem_mo
                        
                        dados.append({
                            "Bitola (Ø)": bitola,
                            "Peso Total (kg)": peso_val,
                            "Custo Material (R$)": custo_mat,
                            "Mão de Obra (R$)": custo_mo,
                            "Total Item (R$)": custo_mat + custo_mo
                        })
                    except:
                        continue

            if dados:
                df = pd.DataFrame(dados)
                st.subheader("📊 Orçamento Detalhado")
                st.table(df.style.format({
                    "Peso Total (kg)": "{:.2f}",
                    "Custo Material (R$)": "{:.2f}",
                    "Mão de Obra (R$)": "{:.2f}",
                    "Total Item (R$)": "{:.2f}"
                }))
                
                total_geral = df["Total Item (R$)"].sum()
                st.metric("VALOR TOTAL DO ORÇAMENTO", f"R$ {total_geral:,.2f}")
            else:
                st.error("A IA não conseguiu formatar os dados. Tente novamente ou verifique se a tabela de resumo está visível.")

doc.close()
