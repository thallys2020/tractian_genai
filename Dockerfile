FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos da aplicação
#COPY . ./
COPY ./ ./

# Atualiza o pip e instala as dependências Python
RUN pip3 install -r requirements.txt

# Exponha as portas necessárias
EXPOSE 8501
EXPOSE 8000

# Copia o script de entrada e define permissões de execução
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Define o comando de entrada
ENTRYPOINT ["/entrypoint.sh"]