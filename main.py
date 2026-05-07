import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Detalhado IA", layout="wide")

st.sidebar.title("⚙️ Configurações")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

st.title("🏗️ Sistema de Orçamento Estrutural Desmembrado")
st.write("Suba o projeto para conferir a listagem item por item.")

# Configurações de Preço e Mão de Obra
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50, help="Valor que você paga no kg do aço")
with col2:
    margem_mo = st.number_input("Sua Porcentagem de Mão de Obra (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Identifica modelos disponíveis para evitar erros de região/versão
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_nome = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in modelos else modelos[0]
        model = genai.GenerativeModel(modelo_nome)
        
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        pag_num = st.number_input(f"Página da Tabela (1 a {len(doc)}):", min_value=1, max_value=len(doc), value=len(doc)) - 1
        
        # Renderização da página
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5)) # Resolução aumentada para leitura precisa
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        st.image(img, caption="Página sendo analisada pela IA")

        if st.button("🔍 Gerar Listagem Detalhada"):
            with st.spinner("IA analisando e calculando item por item..."):
                # Prompt focado em desmembramento
                prompt = """
                Aja como um orçamentista de ferragens. Analise as tabelas de aço desta imagem.
                Preciso que você liste cada elemento encontrado (Ex: Viga V1, Sapata S2, Pilares, ou Resumo por Bitola).
                Para cada item, identifique o Peso Total em kg.
                Retorne os dados EXATAMENTE neste formato de colunas:
                Item | Bitola | Peso
                Exemplo:
                Sapata S1 | 10.0 | 45.5
                Viga V3 | 6.3 | 12.8
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    linhas_dados = []
                    for linha in response.text.strip().split('\n'):
                        if '|' in linha and 'Item' not in linha:
                            try:
                                partes = linha.split('|')
                                nome_item = partes[0].strip()
                                bitola = partes[1].strip()
                                peso_limpo = partes[2].lower().replace('kg', '').replace(',', '.').strip()
                                peso_val = float(peso_limpo)
                                
                                custo_material = peso_val * preco_kg
                                custo_total = custo_material * (1 + margem_mo)
                                
                                linhas_dados.append({
                                    "Descrição do Item": nome_item,
                                    "Bitola (Ø)": bitola,
                                    "Peso (kg)": peso_val,
                                    "Custo Material (R$)": custo_material,
                                    "Venda c/ M.O (R$)": custo_total
                                })
                            except: continue
                    
                    if linhas_dados:
                        df = pd.DataFrame(linhas_dados)
                        
                        st.subheader("📋 Relatório de Itens Identificados")
                        # Tabela formatada para o usuário conferir
                        st.dataframe(df.style.format({
                            "Peso (kg)": "{:.2f}",
                            "Custo Material (R$)": "R$ {:.2f}",
                            "Venda c/ M.O (R$)": "R$ {:.2f}"
                        }), use_container_width=True)
                        
                        # Resumo Geral
                        total_peso = df["Peso (kg)"].sum()
                        total_valor = df["Venda c/ M.O (R$)"].sum()
                        
                        c1, c2 = st.columns(2)
                        c1.metric("Peso Total de Aço", f"{total_peso:.2f} kg")
                        c2.metric("Valor Total do Orçamento", f"R$ {total_valor:,.2f}")
                        
                        st.success("✅ Orçamento gerado! Compare os itens da tabela acima com a sua planta para validar.")
                    else:
                        st.error("A IA não conseguiu identificar os itens no formato esperado. Tente ajustar a página.")
                
    except Exception as e:
        st.error(f"Erro no processamento: {str(e)}")

doc.close()
