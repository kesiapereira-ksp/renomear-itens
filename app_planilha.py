import streamlit as st
import pandas as pd
import zipfile
import io
import re
import unicodedata

# Função para remover acentos (ex: RESCISÕES vira RESCISOES)
def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(texto)) if not unicodedata.combining(c))

# Função auxiliar para limpar e pegar o início do nome da empresa
def gerar_chave_empresa(nome_bruto):
    nome_sem_acento = remover_acentos(nome_bruto)
    nome_limpo = re.sub(r'[^A-Z0-9]', '', nome_sem_acento.upper())
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
        
        col_ordem = st.selectbox("Qual coluna contém a ORDEM (001, 002...)?", colunas, index=colunas.index('Ordem') if 'Ordem' in colunas else 0)
        col_nf = st.selectbox("Qual coluna contém o número da NF (ex: No. Titulo)?", colunas, index=colunas.index('No. Titulo') if 'No. Titulo' in colunas else 0)
        col_empresa = st.selectbox("Qual coluna contém a Empresa (ex: Nome Fornece)?", colunas, index=colunas.index('Nome Fornece') if 'Nome Fornece' in colunas else 0)
        
        if arquivos_enviados and st.button("Cruzar Dados e Renomear"):
            with st.spinner("Analisando NFs e Empresas..."):
                
                # 1. Cria o Dicionário Principal e um Índice por NF para buscas com tolerância
                mapa_arquivos = {}
                mapa_por_nf = {}
                lista_planilha = []
                
                for index, row in df.iterrows():
                    if pd.isna(row[col_ordem]) or pd.isna(row[col_nf]) or pd.isna(row[col_empresa]):
                        continue
                        
                    ordem = str(row[col_ordem]).strip()
                    if ordem.replace('.0', '').isdigit():
                        ordem = str(int(float(ordem))).zfill(3)
                        
                    nf_original = str(row[col_nf]).strip()
                    empresa_original = str(row[col_empresa]).strip()
                        
                    numero_nf = nf_original.lstrip('0')
                    if not numero_nf: 
                        numero_nf = '0'
                        
                    chave_unica = f"{numero_nf}_{gerar_chave_empresa(empresa_original)}"
                    
                    item_info = {
                        'ordem': ordem,
                        'nf_original': nf_original,
                        'numero_nf_limpo': numero_nf,
                        'empresa_original': empresa_original,
                        'encontrado': False
                    }
                    
                    mapa_arquivos[chave_unica] = item_info
                    lista_planilha.append(item_info)
                    
                    if numero_nf not in mapa_por_nf:
                        mapa_por_nf[numero_nf] = []
                    mapa_por_nf[numero_nf].append(item_info)
                
                # 2. Prepara o arquivo ZIP e processa os PDFs
                zip_buffer = io.BytesIO()
                arquivos_renomeados = 0
                arquivos_nao_encontrados = []
                
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for arquivo in arquivos_enviados:
                        nome_original = arquivo.name
                        
                        match_pdf = re.search(r'^(.+?)-(\d+)\.pdf$', nome_original, re.IGNORECASE)
                        
                        if match_pdf:
                            nome_empresa_pdf = match_pdf.group(1).strip()
                            nf_pdf = match_pdf.group(2).lstrip('0')
                            if not nf_pdf:
                                nf_pdf = '0'
                            
                            chave_busca = f"{nf_pdf}_{gerar_chave_empresa(nome_empresa_pdf)}"
                            
                            item_encontrado = None
                            
                            # Teste 1: Chave exata (NF + 8 letras sem acento)
                            if chave_busca in mapa_arquivos and not mapa_arquivos[chave_busca]['encontrado']:
                                item_encontrado = mapa_arquivos[chave_busca]
                            else:
                                # Teste 2: Tolerância (Busca por NF e compara palavras em comum)
                                if nf_pdf in mapa_por_nf:
                                    palavras_pdf = set(re.findall(r'\w{3,}', remover_acentos(nome_empresa_pdf).upper()))
                                    for candidato in mapa_por_nf[nf_pdf]:
                                        if not candidato['encontrado']:
                                            palavras_planilha = set(re.findall(r'\w{3,}', remover_acentos(candidato['empresa_original']).upper()))
                                            if palavras_pdf & palavras_planilha:  # Se houver palavras idênticas
                                                item_encontrado = candidato
                                                break
                            
                            if item_encontrado:
                                item_encontrado['encontrado'] = True
                                ordem_nova = item_encontrado['ordem']
                                
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
                
                # 3. Verifica pendências da planilha
                itens_planilha_sem_pdf = [
                    f"Ordem: {item['ordem']} | NF: {item['nf_original']} | Empresa: {item['empresa_original']}"
                    for item in lista_planilha if not item['encontrado']
                ]
                
                # 4. Exibe os resultados
                st.success(f"🎉 Sucesso! {arquivos_renomeados} arquivos cruzados com precisão.")
                
                if arquivos_nao_encontrados:
                    st.warning(f"⚠️ {len(arquivos_nao_encontrados)} PDFs não acharam correspondência exata na planilha.")
                    with st.expander("Ver PDFs não renomeados"):
                        for arq in arquivos_nao_encontrados:
                            st.write(f"- {arq}")
                
                if itens_planilha_sem_pdf:
                    st.info(f"📋 {len(itens_planilha_sem_pdf)} itens da planilha não possuem um PDF correspondente.")
                    with st.expander("Ver itens da planilha pendentes"):
                        for item in itens_planilha_sem_pdf:
                            st.write(f"- {item}")
                
                st.download_button(
                    label="⬇️ Baixar PDFs Renomeados (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="PDFs_Ordem_Itens.zip",
                    mime="application/zip"
                )
                
    except Exception as e:
        st.error(f"❌ Erro ao processar. Detalhe: {e}")
