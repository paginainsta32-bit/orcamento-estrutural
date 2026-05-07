import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Industrial", layout="wide")

# Inicializa o histórico de itens para não perder o que já foi lido
if 'lista_acumulada' not in st.session_state:
    st.session_state.lista_acumulada = []

st.sidebar.title("⚙️ Painel de Controle")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

if st.sidebar.button("Clear / Novo Orçamento"):
    st.session_state.lista_acumulada = []
    st.rerun()

st.title("🏗️ Orçamentador Estrutural de Alta Capacidade")

col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50)
with col2:
    margem_mo = st.number_input("Mão de Obra (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        pag_num = st.sidebar.number_input(f"Página (1 a {len(doc)}):", min_value=1, max_value=len(doc), value=1) - 1
        
        page = doc.load_page(pag_num)
        # Resolução máxima para não perder nenhum número pequeno
        pix = page.get_pixmap(matrix=fitz.Matrix(3.5, 3.5))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        st.image(img, caption="Documento em processamento", use_column_width=True)

        if st.button("🔍 Extrair TODOS os Itens da Página"):
            with st.spinner("Processando listagem completa... Esta análise é profunda e ignora limites de resumo."):
                # Prompt com técnica de "Listagem Exaustiva"
                prompt = """
                Você é um robô de extração de dados de engenharia. Sua missão é ler a tabela 'RELAÇÃO DE AÇO' e transcrever CADA LINHA sem exceção.
                
                REGRAS CRÍTICAS:
                1. Não agrupe itens. Se houver S1, S2, S3... liste um por um.
                2. Não use 'etc' ou '...'. 
                3. Percorra a tabela do topo até o fim.
                4. Ignore cabeçalhos, pegue apenas os dados.

                Formato de saída:
                Elemento | Bitola | Peso
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    novos_itens = []
                    for linha in response.text.strip().split('\n'):
                        if '|' in linha and 'Bitola' not in linha:
                            try:
                                partes = linha.split('|')
                                nome = partes[0].strip()
                                bitola = partes[1].strip()
                                peso = float(partes[2].lower().replace('kg', '').replace(',', '.').strip())
                                
                                mat = peso * preco_kg
                                novos_itens.append({
                                    "Item": nome,
                                    "Bitola": bitola,
                                    "Peso (kg)": peso,
                                    "Custo Material": mat,
                                    "Total c/ M.O": mat * (1 + margem_mo)
                                })
                            except: continue
                    
                    st.session_state.lista_acumulada = novos_itens

        # Exibição dos resultados
        if st.session_state.lista_acumulada:
            df = pd.DataFrame(st.session_state.lista_acumulada)
            st.subheader(f"📊 Relatório Detalhado: {len(df)} itens extraídos")
            
            st.dataframe(df.style.format({
                "Peso (kg)": "{:.2f}",
                "Custo Material": "R$ {:.2f}",
                "Total c/ M.O": "R$ {:.2f}"
            }), use_container_width=True)
            
            t_peso = df["Peso (kg)"].sum()
            t_valor = df["Total c/ M.O"].sum()
            
            c_a, c_b = st.columns(2)
            c_a.metric("Peso Total (Página)", f"{t_peso:.2f} kg")
            c_b.metric("Total Orçado (Página)", f"R$ {t_valor:,.2f}")

        doc.close()
    except Exception as e:
        st.error(f"Erro: {str(e)}")
