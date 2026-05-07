import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador de Alta Precisão", layout="wide")

if 'dados_orcamento' not in st.session_state:
    st.session_state.dados_orcamento = None

st.sidebar.title("⚙️ Configuração")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

st.title("🏗️ Orçamentador Estrutural Detalhado")
st.write("Extração completa de ferragens para orçamentos profissionais.")

col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50)
with col2:
    margem_mo = st.number_input("Porcentagem de Mão de Obra (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        genai.configure(api_key=api_key)
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_nome = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in modelos else modelos[0]
        model = genai.GenerativeModel(modelo_nome)
        
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        pag_num = st.sidebar.number_input(f"Página do Projeto (1 a {len(doc)}):", 
                                          min_value=1, max_value=len(doc), value=1) - 1
        
        # Aumentamos o Matrix para 3.0 para leitura de letras muito pequenas
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        st.image(img, caption="Imagem em Alta Resolução para Análise", use_column_width=True)

        if st.button("🚀 Gerar Listagem Completa (Sem Resumos)"):
            with st.spinner("Analisando cada linha da tabela... isso pode levar alguns segundos."):
                # Prompt reforçado para não omitir nada
                prompt = """
                Você é um engenheiro orçamentista detalhista. Sua tarefa é extrair TODOS os itens da tabela 'RELAÇÃO DE AÇO' ou 'RESUMO DE AÇO'.
                Não resuma. Se houver 50 itens, liste os 50.
                Procure por Sapatas (S), Pilares (P), Vigas (V), Radier e Blocos.
                
                Retorne os dados EXATAMENTE assim:
                Elemento | Bitola | Peso
                
                Exemplo de saída:
                Viga V1 | 10.0 | 50.2
                Viga V2 | 10.0 | 48.1
                Sapata S1 | 8.0 | 15.3
                ... (continue para todos os itens encontrados)
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    lista_itens = []
                    # Processa a resposta linha por linha
                    for linha in response.text.strip().split('\n'):
                        if '|' in linha and 'Bitola' not in linha:
                            try:
                                partes = linha.split('|')
                                nome = partes[0].strip()
                                bitola = partes[1].strip()
                                peso_texto = partes[2].lower().replace('kg', '').replace(',', '.').strip()
                                peso = float(peso_texto)
                                
                                v_material = peso * preco_kg
                                v_total = v_material * (1 + margem_mo)
                                
                                lista_itens.append({
                                    "Item": nome,
                                    "Bitola": bitola,
                                    "Peso (kg)": peso,
                                    "Custo Material": v_material,
                                    "Total c/ M.O": v_total
                                })
                            except: continue
                    
                    if lista_itens:
                        st.session_state.dados_orcamento = pd.DataFrame(lista_itens)

        if st.session_state.dados_orcamento is not None:
            df = st.session_state.dados_orcamento
            st.subheader(f"📊 Orçamento Detalhado - {len(df)} itens encontrados")
            
            st.dataframe(df.style.format({
                "Peso (kg)": "{:.2f}",
                "Custo Material": "R$ {:.2f}",
                "Total c/ M.O": "R$ {:.2f}"
            }), use_container_width=True)
            
            total_kg = df["Peso (kg)"].sum()
            total_final = df["Total c/ M.O"].sum()
            
            col_a, col_b = st.columns(2)
            col_a.metric("Peso Total Extraído", f"{total_kg:.2f} kg")
            col_b.metric("Total do Orçamento", f"R$ {total_final:,.2f}")
            
            # Opção de baixar o orçamento em Excel/CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Baixar Orçamento em CSV", csv, "orcamento.csv", "text/csv")

        doc.close()
    except Exception as e:
        st.error(f"Erro: {str(e)}")
