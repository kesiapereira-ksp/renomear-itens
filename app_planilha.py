import streamlit as st
import pandas as pd
import zipfile
import io
import re

# Função auxiliar para limpar e pegar o início do nome da empresa
def gerar_chave_empresa(nome_bruto):
    # Deixa tudo maiúsculo, tira espaços/símbolos e pega as 8 primeiras letras
    nome_limpo = re.sub(r'[^A-Z0-9]', '', str(nome_bruto).upper())
    return nome_limpo[:8]

# --- Interface Visual do Site ---
st.title("Renomeador de Renomeador de Itens por Ordem")
st.write("O sistema cruzará os arquivos buscando o número da NF e o Nome da Empresa para evitar duplicidades.")

planilha_enviada = st.file_uploader("1. Envie a Planilha (Excel)", type=["xlsx", "xls"])
arquivos_enviados = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

if planilha_enviada:
    try:
        df = pd.read_excel(planilha_enviada)
        
        st.write("---")
        st.write("⚙️ **Configuração das Colunas**")
        
        colunas = df.columns.tolist()
        col_ordem = st.selectbox("Qual coluna contém a ORDEM (001, 002...)?", colunas)
        col_historico = st.selectbox("Qual coluna contém a NF e a Empresa (ex: Histórico)?", colunas)
        
        if arquivos_enviados and st.button("Cruzar Dados e Renomear"):
            with st.spinner("Analisando NFs e Empresas..."):
                
                # 1. Cria o Dicionário com a CHAVE COMPOSTA (NF + Empresa)
                mapa_arquivos = {}
                for index, row in df.iterrows():
                    if pd.isna(row[col_ordem]) or pd.isna(row[col_historico]):
                        continue
                        
                    ordem = str(row[col_ordem]).strip()
                    if ordem.replace('.0', '').isdigit():
                        ordem = str(int(float(ordem))).zfill(3)
                        
                    historico = str(row[col_historico]).strip()
                    
                    # Procura "NF.123" e pega o texto que vem depois do hífen
                    match_planilha = re.search(r'NF\.0*(\d+)\s*-\s*(.+)', historico, re.IGNORECASE)
                    if match_planilha:
                        numero_nf = match_planilha.group(1)
                        nome_empresa_planilha = match_planilha.group(2)
                        
                        # Cria uma chave única. Ex: "1723_ARODRIGU"
                        chave_unica = f"{numero_nf}_{gerar_chave_empresa(nome_empresa_planilha)}"
                        mapa_arquivos[chave_unica] = ordem
                
                # 2. Prepara o arquivo ZIP
                zip_buffer = io.BytesIO()
                arquivos_renomeados = 0
                arquivos_nao_encontrados = []
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for arquivo in arquivos_enviados:
                        nome_original = arquivo.name
                        
                        # Captura o Nome da Empresa e o número da NF no final do arquivo PDF
                        match_pdf = re.search(r'(?:^\d+\s*-\s*)?(.+?)\s*-0*(\d+)\.pdf$', nome_original, re.IGNORECASE)
                        
                        if match_pdf:
                            nome_empresa_pdf = match_pdf.group(1)
                            nf_pdf = match_pdf.group(2)
                            
                            # Gera a mesma chave única para comparar
                            chave_busca = f"{nf_pdf}_{gerar_chave_empresa(nome_empresa_pdf)}"
                            
                            if chave_busca in mapa_arquivos:
                                ordem_nova = mapa_arquivos[chave_busca]
                                
                                # Limpa a ordem velha do começo e junta a nova
                                nome_limpo = re.sub(r'^\d+\s*-\s*', '', nome_original)
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
                st.success(f"🎉 Sucesso! {arquivos_renomeados} arquivos cruzados com precisão.")
                
                if arquivos_nao_encontrados:
                    st.warning(f"⚠️ {len(arquivos_nao_encontrados)} PDFs não acharam correspondência exata (NF + Empresa) na planilha.")
                
                st.download_button(
                    label="⬇️ Baixar PDFs Renomeados (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="PDFs_Ordem_Itens.zip",
                    mime="application/zip"
                )
                
    except Exception as e:
        st.error(f"❌ Erro ao processar. Detalhe: {e}")
