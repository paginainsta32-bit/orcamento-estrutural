import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
from PIL import Image
import io
import pandas as pd

st.set_page_config(page_title="Orçamentador Detalhado", layout="wide")

# Inicialização de variáveis de estado
if 'dados_orcamento' not in st.session_state:
    st.session_state.dados_orcamento = None

st.sidebar.title("⚙️ Configuração")
api_key = st.sidebar.text_input("Cole sua Gemini API Key:", type="password")

st.title("🏗️ Orçamentador Estrutural Inteligente")
st.write("Gere orçamentos detalhados listando cada elemento do projeto.")

# Configurações de Preço
col1, col2 = st.columns(2)
with col1:
    preco_kg = st.number_input("Preço do KG do Ferro (R$)", value=8.50)
with col2:
    margem_mo = st.number_input("Porcentagem de Mão de Obra (%)", value=25.0) / 100

u_file = st.file_uploader("Suba o PDF do Projeto", type=["pdf"])

if u_file and api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Seleção automática de modelo
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_nome = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in modelos else modelos[0]
        model = genai.GenerativeModel(modelo_nome)
        
        # Abrir PDF
        doc = fitz.open(stream=u_file.read(), filetype="pdf")
        
        st.sidebar.divider()
        pag_num = st.sidebar.number_input(f"Página do Projeto (1 a {len(doc)}):", 
                                          min_value=1, max_value=len(doc), value=1) - 1
        
        # Converter página para imagem
        page = doc.load_page(pag_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        
        st.image(img, caption=f"Analisando Página {pag_num + 1}", use_column_width=True)

        if st.button("🚀 Gerar Listagem Detalhada"):
            with st.spinner("A IA está lendo e calculando cada item..."):
                prompt = """
                Você é um especialista em leitura de projetos estruturais.
                Analise as tabelas de 'RELAÇÃO DE AÇO' e 'RESUMO DE AÇO' na imagem.
                Extraia cada elemento individualmente (ex: Sapata S1, Viga V2, Pilares, Bloco, Radier).
                Para cada item, identifique a Bitola predominante e o Peso Total (kg).
                
                Retorne APENAS no formato:
                Elemento | Bitola | Peso
                Exemplo:
                Sapata S01 | 10.0 | 35.40
                Viga V05 | 6.3 | 12.10
                Pilar P12 | 10.0 | 22.50
                """
                
                response = model.generate_content([prompt, img])
                
                if response.text:
                    lista_itens = []
                    for linha in response.text.strip().split('\n'):
                        if '|' in linha and 'Peso' not in linha:
                            try:
                                partes = linha.split('|')
                                nome = partes[0].strip()
                                bitola = partes[1].strip()
                                peso = float(partes[2].lower().replace('kg', '').replace(',', '.').strip())
                                
                                custo_mat = peso * preco_kg
                                valor_venda = custo_mat * (1 + margem_mo)
                                
                                lista_itens.append({
                                    "Item/Elemento": nome,
                                    "Bitola (Ø)": bitola,
                                    "Peso (kg)": peso,
                                    "Custo Ferro (R$)": custo_mat,
                                    "Total c/ M.O (R$)": valor_venda
                                })
                            except: continue
                    
                    if lista_itens:
                        st.session_state.dados_orcamento = pd.DataFrame(lista_itens)

        # Se houver dados processados, exibe a tabela
        if st.session_state.dados_orcamento is not None:
            df = st.session_state.dados_orcamento
            st.subheader("📊 Orçamento Item por Item")
            
            # Exibição da Tabela
            st.dataframe(df.style.format({
                "Peso (kg)": "{:.2f}",
                "Custo Ferro (R$)": "R$ {:.2f}",
                "Total c/ M.O (R$)": "R$ {:.2f}"
            }), use_container_width=True)
            
            # Totais
            total_kg = df["Peso (kg)"].sum()
            total_final = df["Total c/ M.O (R$)"].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Peso Total Lido", f"{total_kg:.2f} kg")
            c2.metric("Total Geral Orçado", f"R$ {total_final:,.2f}")
            
            st.success("✅ Verifique se os pesos acima batem com a tabela do PDF.")

        doc.close() # Fechamento dentro do bloco onde doc existe

    except Exception as e:
        st.error(f"Erro no processamento: {str(e)}")
else:
    st.info("Aguardando upload do PDF e Chave de API...")
