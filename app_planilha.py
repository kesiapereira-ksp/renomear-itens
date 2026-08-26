import streamlit as st
import pandas as pd
import zipfile
import io
import re

# --- Interface Visual do Site ---
st.title("Renomeador de PDFs por NF 🔄")
st.write("O sistema vai ler a coluna de 'Ordem' e cruzar os arquivos buscando o número da Nota Fiscal (NF).")

# 1. Uploads
planilha_enviada = st.file_uploader("1. Envie a Planilha (Excel)", type=["xlsx", "xls"])
arquivos_enviados = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

if planilha_enviada:
    try:
        df = pd.read_excel(planilha_enviada)
        
        st.write("---")
        st.write("⚙️ **Configuração das Colunas**")
        
        colunas = df.columns.tolist()
        col_ordem = st.selectbox("Qual coluna contém a ORDEM (001, 002...)?", colunas)
        col_historico = st.selectbox("Qual coluna contém a NF (ex: Histórico)?", colunas)
        
        if arquivos_enviados and st.button("Cruzar NFs e Renomear"):
            with st.spinner("Cruzando dados e renomeando..."):
                
                # 1. Cria um "Dicionário" mapeando a NF para a Ordem correta da planilha
                mapa_nfs = {}
                for index, row in df.iterrows():
                    if pd.isna(row[col_ordem]) or pd.isna(row[col_historico]):
                        continue
                        
                    # Pega a ordem e garante que tenha 3 dígitos (ex: 1 vira "001")
                    ordem = str(row[col_ordem]).strip()
                    if ordem.replace('.0', '').isdigit():
                        ordem = str(int(float(ordem))).zfill(3)
                        
                    historico = str(row[col_historico]).strip()
                    
                    # Procura o número após "NF." ignorando zeros à esquerda
                    match_nf_planilha = re.search(r'NF\.0*(\d+)', historico, re.IGNORECASE)
                    if match_nf_planilha:
                        numero_nf = match_nf_planilha.group(1)
                        mapa_nfs[numero_nf] = ordem
                
                # 2. Prepara o arquivo ZIP
                zip_buffer = io.BytesIO()
                arquivos_renomeados = 0
                arquivos_nao_encontrados = []
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for arquivo in arquivos_enviados:
                        nome_original = arquivo.name
                        
                        # Procura o número da NF no final do nome do arquivo PDF
                        # Ex: "001 - texto -000001723.PDF" -> pega o "1723"
                        match_nf_pdf = re.search(r'-0*(\d+)\.pdf$', nome_original.lower())
                        
                        if match_nf_pdf:
                            nf_pdf = match_nf_pdf.group(1)
                            
                            # Se a NF do PDF existir na planilha...
                            if nf_pdf in mapa_nfs:
                                ordem_nova = mapa_nfs[nf_pdf]
                                
                                # Limpa a ordem antiga do começo do nome, se houver (ex: tira o "001 - " velho)
                                nome_limpo = re.sub(r'^\d+\s*-\s*', '', nome_original)
                                
                                # Junta a Ordem nova com o resto do nome do arquivo
                                novo_nome_final = f"{ordem_nova} - {nome_limpo}"
                                
                                zip_file.writestr(novo_nome_final, arquivo.getvalue())
                                arquivos_renomeados += 1
                            else:
                                zip_file.writestr(nome_original, arquivo.getvalue())
                                arquivos_nao_encontrados.append(nome_original)
                        else:
                            zip_file.writestr(nome_original, arquivo.getvalue())
                            arquivos_nao_encontrados.append(nome_original)
                
                # 3. Exibe os resultados
                st.success(f"🎉 Sucesso! {arquivos_renomeados} arquivos cruzados e renomeados.")
                
                if arquivos_nao_encontrados:
                    st.warning(f"⚠️ {len(arquivos_nao_encontrados)} PDFs não tinham NFs compatíveis com a planilha e mantiveram o nome original.")
                
                st.download_button(
                    label="⬇️ Baixar PDFs Renomeados (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="PDFs_NFs_Cruzadas.zip",
                    mime="application/zip"
                )
                
    except Exception as e:
        st.error(f"❌ Erro ao ler a planilha. Detalhe: {e}")
