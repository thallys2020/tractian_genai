# Use uma imagem base Python oficial.
# Escolha uma versão que seja compatível com suas dependências.
FROM python:3.12-slim

# Copia os arquivos de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt ./requirements.txt

# Instala as dependências do backend
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante dos diretórios e arquivos da aplicação

COPY ./ ./

# Garante que o script de inicialização seja executável
RUN chmod +x ./entrypoint.sh

# Cria os diretórios que a API FastAPI pode precisar (se eles não existirem)
# Estes diretórios serão usados para persistência se volumes forem montados.
RUN mkdir -p /app/faiss_index_store && \
    mkdir -p /app/uploaded_pdfs

# Expõe as portas que os aplicativos usarão
# Porta 8000 para a API FastAPI
EXPOSE 8000
# Porta 8501 para o aplicativo Streamlit
EXPOSE 8501

# Define a variável de ambiente GROQ_API_KEY.
# É ALTAMENTE RECOMENDADO passar esta variável em tempo de execução
# em vez de embuti-la aqui por questões de segurança.
# Exemplo: docker run -e GROQ_API_KEY="sua_chave_aqui" ...
# ENV GROQ_API_KEY="SUA_CHAVE_GROQ_AQUI_SE_NECESSARIO_MAS_NAO_RECOMENDADO_EMBUTIR"

# Comando para executar quando o contêiner iniciar
# Executa o script start.sh que gerencia os dois processos
CMD ["./entrypoint.sh"]
