import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Industrial", layout="wide")

if 'memoria_itens' not in st.session_state:
    st.session_state.memoria_itens = []

st.sidebar.title("⚙️ Configurações")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

if st.sidebar.button("🗑️ Limpar Tudo"):
    st.session_state.memoria_itens = []
    st.rerun()

st.title("🏗️ Orçamentador de Alta Performance")

col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50)
with col2:
    margem_mo = st.number_input("Mão de Obra (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        genai.configure(api_key=api_key)
        
        # --- BUSCA AUTOMÁTICA DE MODELO ---
        # Isso evita o erro 404 procurando o nome exato que sua chave permite usar
        modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Tenta o flash, se não achar, usa o primeiro disponível
        modelo_final = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in modelos_disponiveis else modelos_disponiveis[0]
        
        model = genai.GenerativeModel(modelo_final)
        
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        pag_num = st.sidebar.number_input(f"Página (1 a {len(doc)}):", min_value=1, max_value=len(doc), value=len(doc)) - 1
        
        # Alta Resolução
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        st.image(img, caption="Documento pronto para extração total", use_container_width=True)

        if st.button("🚀 Extrair Lista Completa (Sem Cortes)"):
            with st.spinner(f"Usando modelo {modelo_final}. Analisando..."):
                
                # Instrução agressiva para não limitar a 10 itens
                prompt = f"""
                Você é um robô de transcrição de dados. 
                Sua tarefa é ler TODAS as linhas da tabela de aço.
                Não pare após 10 itens. Se houver 100 itens, liste os 100.
                Extraia um por um: Elemento, Bitola e Peso.
                
                Saída esperada:
                Elemento | Bitola | Peso
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    temp_data = []
                    for linha in response.text.strip().split('\n'):
                        if '|' in linha and 'Bitola' not in linha:
                            try:
                                p = linha.split('|')
                                nome = p[0].strip()
                                bit = p[1].strip()
                                peso = float(p[2].lower().replace('kg','').replace(',','.').strip())
                                
                                mat = peso * preco_kg
                                temp_data.append({
                                    "Item": nome,
                                    "Bitola": bit,
                                    "Peso (kg)": peso,
                                    "Material (R$)": mat,
                                    "Venda c/ MO (R$)": mat * (1 + margem_mo)
                                })
                            except: continue
                    
                    st.session_state.memoria_itens = temp_data

        if st.session_state.memoria_itens:
            df = pd.DataFrame(st.session_state.memoria_itens)
            st.subheader(f"📋 Itens Encontrados: {len(df)}")
            st.dataframe(df, use_container_width=True)
            
            t_peso = df["Peso (kg)"].sum()
            t_total = df["Venda c/ MO (R$)"].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Peso Total", f"{t_peso:.2f} kg")
            c2.metric("Total Orçamento", f"R$ {t_total:,.2f}")

        doc.close()
    except Exception as e:
        st.error(f"Erro detectado: {e}")
        st.info("Se o erro for 404, verifique se sua API Key foi criada para o plano 'Gemini API' no Google AI Studio.")
