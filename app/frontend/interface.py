# streamlit_app.py
# Bibliotecas necessárias:
# pip install streamlit requests

import streamlit as st
import requests # Para fazer chamadas HTTP para a API FastAPI
import io # Para lidar com os bytes dos arquivos

# --- Configuração da Aplicação Streamlit ---
st.set_page_config(page_title="PDF Q&A com LLM", layout="wide")

# URL base da API FastAPI (certifique-se de que seu backend FastAPI esteja rodando neste endereço)
API_BASE_URL = "http://localhost:8000"
DOCUMENTS_ENDPOINT = f"{API_BASE_URL}/documents"
QUESTION_ENDPOINT = f"{API_BASE_URL}/question"
RESET_ENDPOINT = f"{API_BASE_URL}/reset_index"

# --- Funções Auxiliares ---

def upload_pdfs_to_api(uploaded_files_list):
    """
    Envia os arquivos PDF para o endpoint /documents da API.
    """
    if not uploaded_files_list:
        st.warning("Por favor, selecione um ou mais arquivos PDF para fazer o upload.")
        return None

    # Prepara os arquivos para a requisição multipart/form-data
    # A API espera uma lista de arquivos sob a chave 'files'
    files_to_send = []
    for uploaded_file in uploaded_files_list:
        # Garante que o ponteiro do arquivo está no início
        uploaded_file.seek(0)
        # Adiciona à lista no formato esperado por requests (nome_do_campo, (nome_do_arquivo, fileobj, tipo_conteudo))
        files_to_send.append(('files', (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)))

    try:
        with st.spinner("Processando documentos... Isso pode levar alguns instantes."):
            response = requests.post(DOCUMENTS_ENDPOINT, files=files_to_send)
        response.raise_for_status() # Levanta um erro para códigos de status HTTP 4xx/5xx
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Erro de conexão: Não foi possível conectar à API em {API_BASE_URL}. Verifique se o servidor FastAPI está em execução.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro HTTP ao fazer upload dos documentos: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao fazer upload dos documentos: {e}")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado durante o upload: {e}")
        return None

def ask_question_to_api(question_text):
    """
    Envia a pergunta para o endpoint /question da API.
    """
    if not question_text.strip():
        st.warning("Por favor, insira uma pergunta.")
        return None

    payload = {"question": question_text}
    try:
        with st.spinner("Buscando a resposta..."):
            response = requests.post(QUESTION_ENDPOINT, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Erro de conexão: Não foi possível conectar à API em {API_BASE_URL}. Verifique se o servidor FastAPI está em execução.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro HTTP ao fazer a pergunta: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao fazer a pergunta: {e}")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao buscar a resposta: {e}")
        return None

def reset_vector_store_on_api():
    """
    Envia uma requisição para resetar o índice de vetores na API.
    """
    try:
        with st.spinner("Resetando o índice de documentos..."):
            response = requests.post(RESET_ENDPOINT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"Erro de conexão: Não foi possível conectar à API em {API_BASE_URL}. Verifique se o servidor FastAPI está em execução.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"Erro HTTP ao resetar o índice: {e.response.status_code} - {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao resetar o índice: {e}")
        return None
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao resetar o índice: {e}")
        return None

# --- Interface do Usuário Streamlit ---

st.title("📄 Sistema de Perguntas e Respostas sobre Documentos PDF")
st.markdown("""
Bem-vindo! Faça o upload de seus documentos PDF, aguarde o processamento e, em seguida, faça perguntas sobre o conteúdo deles.
O sistema utiliza um LLM (API do Groq) para fornecer respostas contextuais.
""")

# Seção de Upload de Documentos
st.header("1. Faça o Upload dos seus Documentos PDF")
uploaded_files = st.file_uploader(
    "Selecione um ou mais arquivos PDF",
    type="pdf",
    accept_multiple_files=True,
    help="Você pode arrastar e soltar arquivos aqui ou clicar para navegar."
)

if uploaded_files:
    st.write(f"{len(uploaded_files)} arquivo(s) selecionado(s):")
    for uploaded_file in uploaded_files:
        st.write(f"- {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)")

    if st.button("Processar Documentos Selecionados", key="process_docs_button"):
        api_response = upload_pdfs_to_api(uploaded_files)
        if api_response:
            st.success(api_response.get("message", "Documentos processados."))
            st.info(f"Total de documentos indexados: {api_response.get('documents_indexed', 'N/A')}")
            st.info(f"Total de chunks gerados: {api_response.get('total_chunks_generated', 'N/A')}")
            # Limpa os arquivos da UI após o upload para evitar reenvio acidental
            # st.experimental_rerun() # Pode ser útil, mas vamos evitar por enquanto para manter a mensagem de sucesso
else:
    st.info("Aguardando o upload de arquivos PDF.")

st.divider()

# Seção de Perguntas e Respostas
st.header("2. Faça uma Pergunta sobre os Documentos")

# Verifica se há documentos processados (uma forma simples, pode ser melhorada com estado)
# Idealmente, a API deveria informar se está pronta para receber perguntas.
# Por agora, vamos assumir que se o usuário chegou aqui, ele já fez upload.

question = st.text_input(
    "Digite sua pergunta aqui:",
    placeholder="Ex: Qual é o consumo de energia do motor?"
)

if st.button("Obter Resposta", key="ask_question_button", disabled=not question):
    if not question.strip():
        st.warning("Por favor, digite uma pergunta válida.")
    else:
        api_response = ask_question_to_api(question)
        if api_response:
            st.subheader("Resposta:")
            st.markdown(api_response.get("answer", "Nenhuma resposta recebida."))

            source_documents = api_response.get("source_documents")
            if source_documents:
                st.subheader("Fontes Consultadas (Trechos dos Documentos):")
                for i, doc_info in enumerate(source_documents):
                    with st.expander(f"Fonte {i+1}: {doc_info.get('source_filename', 'Desconhecida')}", expanded=False):
                        st.caption(f"Arquivo: {doc_info.get('source_filename', 'Desconhecida')}")
                        st.markdown(f"> {doc_info.get('content_preview', 'Conteúdo não disponível.')}")
            else:
                st.info("Nenhum documento de origem foi retornado com a resposta.")
elif not question and st.session_state.get("ask_question_button"): # Se o botão foi clicado mas a pergunta estava vazia
    st.warning("Por favor, digite uma pergunta.")


st.divider()

# Seção de Administração (Opcional)
with st.sidebar:
    st.header("Opções Administrativas")
    if st.button("Limpar Base de Documentos (Resetar Índice)", key="reset_index_button"):
        confirmation = st.radio(
            "Tem certeza que deseja apagar todos os documentos indexados? Esta ação não pode ser desfeita.",
            ("Não", "Sim"),
            key="reset_confirm",
            horizontal=True
        )
        if confirmation == "Sim":
            api_response = reset_vector_store_on_api()
            if api_response:
                st.success(api_response.get("message", "Índice resetado com sucesso."))
                st.info("A base de documentos foi limpa. Você precisará fazer upload de novos PDFs.")
            else:
                st.error("Falha ao resetar o índice.")
            # Forçar um rerun para limpar o estado da confirmação
            st.experimental_rerun()


st.markdown("---")
st.caption("Desenvolvido como parte de um desafio de Engenharia de Machine Learning.")
