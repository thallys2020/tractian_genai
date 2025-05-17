#!/bin/bash

# Define o diretório base da aplicação dentro do contêiner
APP_DIR="/app"

# Navega para o diretório do backend e inicia a API FastAPI em segundo plano
echo "Iniciando API FastAPI na porta 8000..."
python app/backend/main.py &

# Aguarda alguns segundos para garantir que a API tenha tempo de iniciar
# Isso é opcional, mas pode ajudar a evitar problemas de conexão imediata do frontend
echo "Aguardando a API iniciar..."
sleep 10 # Ajuste o tempo conforme necessário

# Navega para o diretório do frontend e inicia o aplicativo Streamlit em primeiro plano
echo "Iniciando aplicativo Streamlit na porta 8501..."
# --server.headless=true é importante para rodar Streamlit em ambientes sem GUI (como Docker)
# --server.address=0.0.0.0 permite que o Streamlit seja acessado de fora do contêiner
# --server.enableCORS=false pode ser necessário dependendo da configuração, mas geralmente não para localhost
streamlit run app/frontend/interface.py --server.port 8501 --server.address 0.0.0.0 --server.headless true

# O comando 'streamlit run' manterá o contêiner em execução.
# Se o Streamlit parar por algum motivo, o script e, consequentemente, o contêiner, terminarão.