## Tractian: RAG Workflow API with a Streamlit Front-end

O projeto em questão se tratar da implementação de um sistema de tratamento e correção de planilhas, utilizando GenAI com Amazon Bedrock juntamente ao Pandas Agent (LangChain).

## 🚀 Começando

Essas instruções permitirão que você esteja hábil utilizar a ferramenta de forma correta. 

### 📋 Pré-requisitos

1. Na raiz do projeto, crie o arquivo ```.env```, com variáveis semelhantes as presentes no arquivo ```.env.example```.

2. Faça o build da image utilizando o comando:

```shell
docker build . -t tractian-rag
```

2. Execute o container com a imagem criada anteriormente, utilizando o comando:

```shell
docker run tractian-rag
```


## 🔩 Interagindo com a Solução

Após inicializar a API você poderá acessá-la (documentação e chamadas), via o seguinte end-point:

### Swagger API:

Será disponibilizada a documentação da API no seguinte endpoint local:
```
http://localhost:8000/docs
```
Contendo as rotas:
- /documents: enviar documentos em PDF para armazenar em banco de dados indexado localmente (FAISS);
- /question: enviar string referente à pergunta do usuário sobre os documentos enviados na rota ```/documents```;
- /reset_index: reinicializar indexação de vector store;


### API Contract

This document outlines the contract for the LLM API, which allows for document processing and question answering based on the indexed documents.

#### Endpoints

#### 1. Document Processing

This endpoint is used to upload and process PDF documents. The content of these documents will be indexed for subsequent question answering.

* **URL:** `/documents` (Assuming this is the endpoint for the first example; please adjust if different)
* **Method:** `POST`
* **Description:** Accepts one or more PDF files, processes them, and indexes their content.

#### Request

* **Headers:**
    * `Content-Type: multipart/form-data`
* **Body:**
    * `files`: (file | array<file>) - One or more PDF files. Each file should be sent under this field name.

**Example cURL Request:**

```bash
curl -X POST \
  http://localhost:8000/upload \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@/path/to/your/document1.pdf' \
  -F 'files=@/path/to/your/document2.pdf'
```
#### Response (Success: 200 OK)

Headers:

    Content-Type: application/json

Body:
```
{
    "message": "Documents processed successfully",
    "documents_indexed": 2,
    "total_chunks": 128
}
```
- message (string): A confirmation message indicating the outcome of the operation.

- documents_indexed (integer): The number of documents successfully processed and indexed from the request.

- total_chunks (integer): The total number of text chunks generated and indexed from the processed documents.

#### 2. Question Answering

This endpoint is used to ask a question related to the content of the previously uploaded and indexed documents.

- URL: /question

- Method: POST

- Description: Accepts a question in JSON format and returns an answer based on the indexed documents.

#### Request

Headers:

    Content-Type: application/json

Body:

    {
    "question": "What is the power consumption of the motor?"
    }

- question (string): The question you want to ask about the documents.

#### Example cURL Request:

    curl -X POST \
    http://localhost:8000/question \
    -H 'Content-Type: application/json' \
    -d '{
        "question": "What is the power consumption of the motor?"
    }'

#### Response (Success: 200 OK)

Headers:

    Content-Type: application/json

Body:

    {
    "answer": "The power consumption of the motor is 2.3 kW."
    }

- answer (string): The answer to the question, derived from the indexed documents. If the information is not found or an error occurs, the message should indicate this.


### UI interface App:

Caso o usuário queira acessar o processador inteligente de documentos de uma maneira mais intuitiva, segere-se utilizar a interface gráfica steamlit pelo endereço: ```http://localhost:8501```.

Neste caso, será mostrada a seguinte tela:

## 🤝 Agradecimentos

* Agradecemos por toda a atenção durante o projeto. Qualquer dúvida é só chamar. 📢