import streamlit as st
import google.generativeai as genai
import google.api_core.exceptions as google_exceptions
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

# Configuração visual do Streamlit
st.set_page_config(page_title="Orçamentador Inteligente IA", layout="wide")

st.sidebar.title("⚙️ Configurações")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")
st.sidebar.info("Obtenha sua chave em: https://aistudio.google.com/app/apikey")

st.title("🏗️ Orçamentador de Ferragens Pro")
st.markdown("""
Esta ferramenta utiliza Inteligência Artificial para ler tabelas de projetos estruturais.
1. Insira sua API Key ao lado.
2. Suba o PDF do projeto.
3. Escolha a página onde está o **Resumo do Aço**.
""")

# Parâmetros de Cálculo
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50, step=0.10)
with col2:
    margem_mo = st.number_input("Mão de Obra e Lucro (%)", value=25.0, step=1.0) / 100

u_file = st.file_uploader("📂 Envie o arquivo PDF do Projeto", type=["pdf"])

if u_file:
    # Abrir o PDF
    doc = fitz.open(stream=u_file.read(), filetype="pdf")
    total_paginas = len(doc)
    
    # Seleção de página (Muitas vezes a tabela de aço está na última página)
    pag_num = st.number_input(f"Selecione a página da tabela (Total: {total_paginas})", 
                              min_value=1, max_value=total_paginas, value=total_paginas) - 1
    
    # Processar a página escolhida como imagem
    with st.spinner("Renderizando página..."):
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5)) # Alta resolução
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        st.image(img, caption=f"Página {pag_num + 1} selecionada", use_column_width=True)

    if st.button("🚀 Gerar Orçamento Completo"):
        if not api_key:
            st.error("❌ Por favor, insira a API Key na barra lateral.")
        else:
            try:
                # Configurar IA
                genai.configure(api_key=api_key)
                # Uso do nome completo do modelo para evitar erro NotFound
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                
                with st.spinner("IA analisando dados estruturais..."):
                    prompt = """
                    Analise a imagem deste projeto de engenharia.
                    Localize especificamente a tabela de 'RESUMO DO AÇO'.
                    Extraia a Bitola (diâmetro Ø) e o PESO TOTAL (kg) para cada tipo de ferro.
                    Ignore outras tabelas como 'Relação de Peças'.
                    Responda APENAS no formato: Bitola | Peso
                    Exemplo:
                    5.0 | 45.2
                    10.0 | 120.8
                    """
                    
                    response = model.generate_content([prompt, img])
                    
                    if not response.text:
                        st.error("A IA não retornou dados. Verifique se a imagem está nítida.")
                    else:
                        # Processar a resposta texto para DataFrame
                        dados = []
                        linhas = response.text.strip().split('\n')
                        
                        for l in linhas:
                            if '|' in l:
                                try:
                                    partes = l.split('|')
                                    bitola = partes[0].strip()
                                    # Limpa strings e converte vírgula brasileira em ponto
                                    peso_limpo = partes[1].lower().replace('kg', '').replace(',', '.').strip()
                                    peso_val = float(peso_limpo)
                                    
                                    v_material = peso_val * preco_kg
                                    v_mo = v_material * margem_mo
                                    
                                    dados.append({
                                        "Bitola (Ø)": bitola,
                                        "Peso (kg)": peso_val,
                                        "Material (R$)": v_material,
                                        "Mão de Obra (R$)": v_mo,
                                        "Subtotal (R$)": v_material + v_mo
                                    })
                                except:
                                    continue
                        
                        if dados:
                            df = pd.DataFrame(dados)
                            st.subheader("📋 Orçamento Desmembrado")
                            st.table(df.style.format({
                                "Peso (kg)": "{:.2f}",
                                "Material (R$)": "R$ {:.2f}",
                                "Mão de Obra (R$)": "R$ {:.2f}",
                                "Subtotal (R$)": "R$ {:.2f}"
                            }))
                            
                            total_geral = df["Subtotal (R$)"].sum()
                            st.divider()
                            st.metric(label="VALOR TOTAL DO ORÇAMENTO", value=f"R$ {total_geral:,.2f}")
                        else:
                            st.warning("Não foi possível identificar dados na tabela. Verifique se escolheu a página correta.")

            except google_exceptions.NotFound:
                st.error("❌ Erro: Modelo 'gemini-1.5-flash' não encontrado. Verifique sua região ou a versão da biblioteca.")
            except Exception as e:
                st.error(f"❌ Ocorreu um erro: {str(e)}")
    
    doc.close()
