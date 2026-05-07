import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Pro v3", layout="wide")

if 'lista_acumulada' not in st.session_state:
    st.session_state.lista_acumulada = []

st.sidebar.title("⚙️ Configuração")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

if st.sidebar.button("Limpar Dados / Novo Projeto"):
    st.session_state.lista_acumulada = []
    st.rerun()

st.title("🏗️ Orçamentador Estrutural de Alta Performance")

col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50)
with col2:
    margem_mo = st.number_input("Mão de Obra (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Ajuste aqui: Usando o nome 'gemini-1.5-flash-latest' que é mais estável
        # E configurando para aceitar respostas muito longas (max_output_tokens)
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-latest',
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "max_output_tokens": 8192, # Aumentado para não cortar a lista
            }
        )
        
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        pag_num = st.sidebar.number_input(f"Página (1 a {len(doc)}):", min_value=1, max_value=len(doc), value=1) - 1
        
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0)) # Resolução ideal
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        st.image(img, caption="Documento pronto para análise exaustiva", use_column_width=True)

        if st.button("🔍 Extrair Lista Completa de Ferragens"):
            with st.spinner("Analisando cada milímetro da tabela... Por favor, aguarde."):
                
                prompt = """
                MISSÃO: Transcrever TODAS as linhas das tabelas de aço presentes nesta imagem.
                
                REGRAS DE OURO:
                1. Liste cada elemento individualmente (ex: Sapata S1, Sapata S2, Viga V10, Pilar P5).
                2. Capture a Bitola (diâmetro) e o Peso Total em kg.
                3. NÃO RESUMA. Se a lista for longa, continue até o fim.
                4. Ignore textos explicativos, foque apenas nos dados da tabela.

                SAÍDA OBRIGATÓRIA (Separada por barra vertical):
                Elemento | Bitola | Peso
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    novos_itens = []
                    for linha in response.text.strip().split('\n'):
                        if '|' in linha and 'Bitola' not in linha:
                            try:
                                partes = linha.split('|')
                                if len(partes) >= 3:
                                    nome = partes[0].strip()
                                    bitola = partes[1].strip()
                                    # Limpeza de números brasileiros
                                    peso_str = partes[2].lower().replace('kg', '').replace(',', '.').strip()
                                    peso = float(peso_str)
                                    
                                    valor_material = peso * preco_kg
                                    novos_itens.append({
                                        "Elemento": nome,
                                        "Bitola": bitola,
                                        "Peso (kg)": peso,
                                        "Material (R$)": valor_material,
                                        "Total c/ M.O (R$)": valor_material * (1 + margem_mo)
                                    })
                            except: continue
                    
                    st.session_state.lista_acumulada = novos_itens

        if st.session_state.lista_acumulada:
            df = pd.DataFrame(st.session_state.lista_acumulada)
            st.subheader(f"📋 Itens Identificados: {len(df)}")
            
            st.dataframe(df.style.format({
                "Peso (kg)": "{:.2f}",
                "Material (R$)": "R$ {:.2f}",
                "Total c/ M.O (R$)": "R$ {:.2f}"
            }), use_container_width=True)
            
            t_peso = df["Peso (kg)"].sum()
            t_venda = df["Total c/ M.O (R$)"].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Peso Total Extraído", f"{t_peso:.2f} kg")
            c2.metric("Total do Orçamento", f"R$ {t_venda:,.2f}")

        doc.close()
    except Exception as e:
        # Se o erro 404 persistir, mostramos uma mensagem clara
        if "404" in str(e):
            st.error("Erro de Conexão com o Modelo: O Google está atualizando os servidores. Tente novamente em alguns minutos ou verifique sua API Key.")
        else:
            st.error(f"Erro inesperado: {str(e)}")
