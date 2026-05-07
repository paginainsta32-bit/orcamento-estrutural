import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Pro", layout="wide")

# Inicialização de memória
if 'lista_itens' not in st.session_state:
    st.session_state.lista_itens = []

st.sidebar.title("⚙️ Painel de Controle")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

if st.sidebar.button("Limpar Tudo / Novo Projeto"):
    st.session_state.lista_itens = []
    st.rerun()

st.title("🏗️ Orçamentador de Ferragens")

col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50)
with col2:
    margem_mo = st.number_input("Mão de Obra (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        # Configuração simplificada da API
        genai.configure(api_key=api_key)
        
        # Tentativa com o nome de modelo mais compatível
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        total_pags = len(doc)
        pag_num = st.sidebar.number_input(f"Página (1 a {total_pags}):", min_value=1, max_value=total_pags, value=total_pags) - 1
        
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        st.image(img, caption="Página carregada", use_container_width=True)

        if st.button("🚀 Extrair Lista Completa"):
            with st.spinner("Analisando tabela..."):
                prompt = """
                Aja como um extrator de dados. Leia a tabela de aço da imagem.
                Extraia CADA LINHA individualmente. Não resuma.
                Se houver Sapata S1, S2, S3... liste todas.
                
                Saída esperada:
                Elemento | Bitola | Peso
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    
                    if response.text:
                        temp_list = []
                        for linha in response.text.strip().split('\n'):
                            if '|' in linha and 'Bitola' not in linha:
                                try:
                                    p = linha.split('|')
                                    nome = p[0].strip()
                                    bit = p[1].strip()
                                    peso = float(p[2].lower().replace('kg','').replace(',','.').strip())
                                    
                                    v_mat = peso * preco_kg
                                    temp_list.append({
                                        "Elemento": nome,
                                        "Bitola": bit,
                                        "Peso (kg)": peso,
                                        "Material (R$)": v_mat,
                                        "Total c/ MO (R$)": v_mat * (1 + margem_mo)
                                    })
                                except: continue
                        
                        st.session_state.lista_itens = temp_list
                except Exception as e_api:
                    st.error(f"Erro na API do Google: {e_api}")
                    st.info("Dica: Verifique se sua chave API está correta no Google AI Studio.")

        if st.session_state.lista_itens:
            df = pd.DataFrame(st.session_state.lista_itens)
            st.subheader(f"📋 Itens Identificados ({len(df)})")
            st.dataframe(df, use_container_width=True)
            
            t_peso = df["Peso (kg)"].sum()
            t_valor = df["Total c/ MO (R$)"].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Peso Total", f"{t_peso:.2f} kg")
            c2.metric("Total Orçamento", f"R$ {t_valor:,.2f}")

        doc.close()
    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
