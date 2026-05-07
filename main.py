import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Inteligente", layout="wide")

st.sidebar.title("⚙️ Configuração")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

st.title("🏗️ Orçamentador de Ferragens")

# Configurações de Preço
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50)
with col2:
    margem_mo = st.number_input("Mão de Obra e Lucro (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        # Inicializa a API
        genai.configure(api_key=api_key)
        
        # --- FUNÇÃO PARA ESCOLHER O MELHOR MODELO DISPONÍVEL ---
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Tenta o flash primeiro, se não tiver, pega o primeiro da lista
        modelo_nome = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in modelos_disponiveis else modelos_disponiveis[0]
        model = genai.GenerativeModel(modelo_nome)
        
        # Processar PDF
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        pag_num = st.number_input(f"Página da Tabela (1 a {len(doc)}):", min_value=1, max_value=len(doc), value=len(doc)) - 1
        
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        st.image(img, caption="Visualizando página selecionada")

        if st.button("🚀 Analisar com IA"):
            with st.spinner(f"Usando modelo: {modelo_nome}..."):
                prompt = """
                Extraia a tabela de 'RESUMO DO AÇO'.
                Retorne APENAS: Bitola | Peso
                Exemplo:
                5.0 | 100.5
                12.5 | 45.0
                """
                response = model.generate_content([prompt, img])
                
                if response.text:
                    dados = []
                    for linha in response.text.strip().split('\n'):
                        if '|' in linha:
                            try:
                                b, p = linha.split('|')
                                peso = float(p.replace(',', '.').strip())
                                mat = peso * preco_kg
                                dados.append({
                                    "Bitola": b.strip(),
                                    "Peso (kg)": peso,
                                    "Material": mat,
                                    "Mão de Obra": mat * margem_mo,
                                    "Total": mat * (1 + margem_mo)
                                })
                            except: continue
                    
                    if dados:
                        df = pd.DataFrame(dados)
                        st.table(df)
                        st.success(f"Total Geral: R$ {df['Total'].sum():.2f}")
                    else:
                        st.error("IA leu, mas não formatou os dados. Tente novamente.")
                
    except Exception as e:
        st.error(f"Erro: {str(e)}")
        st.info("Verifique se sua chave de API está ativa e se você tem acesso aos modelos 1.5 no Google AI Studio.")
