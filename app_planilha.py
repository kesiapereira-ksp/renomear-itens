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
st.title("Renomeador de Itens por Ordem")
st.write("O sistema cruzará os arquivos buscando o número da NF e o Nome da Empresa para evitar duplicidades.")

planilha_enviada = st.file_uploader("1. Envie a Planilha (Excel)", type=["xlsx", "xls"])
arquivos_enviados = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

if planilha_enviada:
    try:
        df = pd.read_excel(planilha_enviada)
        
        st.write("---")
        st.write("⚙️ **Configuração das Colunas**")
        
        colunas = df.columns.tolist()
        
        # Seleção das colunas baseadas na sua planilha
        col_ordem = st.selectbox("Qual coluna contém a ORDEM (001, 002...)?", colunas, index=colunas.index('Ordem') if 'Ordem' in colunas else 0)
        col_nf = st.selectbox("Qual coluna contém o número da NF (ex: No. Titulo)?", colunas, index=colunas.index('No. Titulo') if 'No. Titulo' in colunas else 0)
        col_empresa = st.selectbox("Qual coluna contém a Empresa (ex: Nome Fornece)?", colunas, index=colunas.index('Nome Fornece') if 'Nome Fornece' in colunas else 0)
        
        if arquivos_enviados and st.button("Cruzar Dados e Renomear"):
            with st.spinner("Analisando NFs e Empresas..."):
                
                # 1. Cria o Dicionário com a CHAVE COMPOSTA (NF + Empresa)
                mapa_arquivos = {}
                for index, row in df.iterrows():
                    # Ignora a linha se faltar algum dos dados
                    if pd.isna(row[col_ordem]) or pd.isna(row[col_nf]) or pd.isna(row[col_empresa]):
                        continue
                        
                    # Trata a Ordem (garante que fique no formato 001, 002, etc)
                    ordem = str(row[col_ordem]).strip()
                    if ordem.replace('.0', '').isdigit():
                        ordem = str(int(float(ordem))).zfill(3)
                        
                    # Trata o número da NF da planilha (tira zeros da esquerda pra evitar erros de cruzamento)
                    numero_nf = str(row[col_nf]).strip().lstrip('0')
                    if not numero_nf: 
                        numero_nf = '0'
                        
                    # Trata o nome da empresa
                    nome_empresa_planilha = str(row[col_empresa]).strip()
                        
                    # Cria a chave única. Ex: "594_KEYCONSU"
                    chave_unica = f"{numero_nf}_{gerar_chave_empresa(nome_empresa_planilha)}"
                    mapa_arquivos[chave_unica] = ordem
                
                # 2. Prepara o arquivo ZIP
                zip_buffer = io.BytesIO()
                arquivos_renomeados = 0
                arquivos_nao_encontrados = []
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for arquivo in arquivos_enviados:
                        nome_original = arquivo.name
                        
                        # --- LEITURA DO ARQUIVO PDF ---
                        # Formato esperado: "NOME DA EMPRESA-NUMERONF.PDF"
                        match_pdf = re.search(r'^(.+?)-(\d+)\.pdf$', nome_original, re.IGNORECASE)
                        
                        if match_pdf:
                            nome_empresa_pdf = match_pdf.group(1).strip()
                            
                            # Pega o número da nota do PDF e também tira os zeros à esquerda
                            nf_pdf = match_pdf.group(2).lstrip('0')
                            if not nf_pdf:
                                nf_pdf = '0'
                            
                            # Gera a mesma chave única para comparar com a planilha
                            chave_busca = f"{nf_pdf}_{gerar_chave_empresa(nome_empresa_pdf)}"
                            
                            if chave_busca in mapa_arquivos:
                                ordem_nova = mapa_arquivos[chave_busca]
                                
                                # Limpa a ordem velha do começo do arquivo (se houver) e junta a nova
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
                    with st.expander("Ver arquivos que não foram renomeados"):
                        for arq in arquivos_nao_encontrados:
                            st.write(arq)
                
                st.download_button(
                    label="⬇️ Baixar PDFs Renomeados (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="PDFs_Ordem_Itens.zip",
                    mime="application/zip"
                )
                
    except Exception as e:
        st.error(f"❌ Erro ao processar. Detalhe: {e}")
