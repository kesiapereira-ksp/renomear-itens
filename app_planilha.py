import streamlit as st
import pandas as pd
import zipfile
import io

# --- Interface Visual do Site ---
st.title("Renomeador de PDFs por Planilha 📊📄")
st.write("Faça o upload da sua planilha de controle e dos PDFs originais. O sistema cruzará os dados e renomeará tudo automaticamente.")

# 1. Upload da Planilha
planilha_enviada = st.file_uploader("1. Envie a Planilha (Excel)", type=["xlsx", "xls"])

# 2. Upload dos PDFs
arquivos_enviados = st.file_uploader("2. Envie os PDFs", type=["pdf"], accept_multiple_files=True)

if planilha_enviada:
    try:
        # Lê a planilha usando o pandas
        df = pd.read_excel(planilha_enviada)
        
        st.write("✅ **Planilha carregada! Pré-visualização:**")
        st.dataframe(df.head(3)) # Mostra as 3 primeiras linhas para conferência
        
        st.write("---")
        st.write("⚙️ **Configuração das Colunas**")
        
        # Cria menus drop-down com os nomes das colunas da planilha do usuário
        colunas = df.columns.tolist()
        col_origem = st.selectbox("Qual coluna contém o NOME ATUAL do arquivo?", colunas)
        col_destino = st.selectbox("Qual coluna contém o NOVO NOME do arquivo?", colunas)
        
        if arquivos_enviados and st.button("Renomear Documentos"):
            with st.spinner("Cruzando dados e renomeando..."):
                
                # Cria um dicionário (mapa) ligando o nome velho ao nome novo
                mapa_nomes = {}
                for index, row in df.iterrows():
                    # Ignora linhas vazias
                    if pd.isna(row[col_origem]) or pd.isna(row[col_destino]):
                        continue
                        
                    nome_velho = str(row[col_origem]).strip()
                    nome_novo = str(row[col_destino]).strip()
                    
                    # Remove a palavra ".pdf" se o usuário tiver digitado na planilha, para evitar erros
                    if nome_velho.lower().endswith(".pdf"):
                        nome_velho = nome_velho[:-4]
                    if nome_novo.lower().endswith(".pdf"):
                        nome_novo = nome_novo[:-4]
                        
                    mapa_nomes[nome_velho.lower()] = nome_novo
                
                # Prepara o arquivo ZIP na memória
                zip_buffer = io.BytesIO()
                arquivos_renomeados = 0
                arquivos_nao_encontrados = []
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for arquivo in arquivos_enviados:
                        nome_original = arquivo.name
                        nome_base = nome_original.lower()
                        
                        if nome_base.endswith(".pdf"):
                            nome_base = nome_base[:-4]
                            
                        # Verifica se o nome do PDF está listado na planilha
                        if nome_base in mapa_nomes:
                            novo_nome_final = mapa_nomes[nome_base] + ".pdf"
                            zip_file.writestr(novo_nome_final, arquivo.getvalue())
                            arquivos_renomeados += 1
                        else:
                            # Se não achar na planilha, guarda no ZIP com o nome original
                            zip_file.writestr(nome_original, arquivo.getvalue())
                            arquivos_nao_encontrados.append(nome_original)
                
                # Exibe o resultado na tela
                st.success(f"🎉 Sucesso! {arquivos_renomeados} arquivos renomeados.")
                
                if arquivos_nao_encontrados:
                    st.warning(f"⚠️ {len(arquivos_nao_encontrados)} arquivos não constavam na planilha e mantiveram o nome original.")
                
                # Botão de Download do ZIP pronto
                st.download_button(
                    label="⬇️ Baixar Arquivos Renomeados (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="PDFs_Renomeados_Planilha.zip",
                    mime="application/zip"
                )
                
    except Exception as e:
        st.error(f"❌ Erro ao ler a planilha. Detalhe: {e}")

elif arquivos_enviados and not planilha_enviada:
    st.info("⚠️ Envie a planilha primeiro para liberar as opções de renomeação.")
