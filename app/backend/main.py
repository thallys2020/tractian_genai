import os
import shutil # For cleaning up storage and directories
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from utils import *


# --- FastAPI App Initialization ---
app = FastAPI(
    title="PDF Q&A System with LLM",
    description="Upload PDF documents and ask questions about their content using Groq LLM and FAISS.",
    version="1.0.0"
)

# Load the vector store on application startup
@app.on_event("startup")
async def startup_event():
    print("Application startup: Attempting to load FAISS vector store.")
    load_vector_store()

# --- API Endpoints ---

@app.post("/documents", response_model=DocumentUploadResponse)
async def upload_documents_endpoint(files: List[UploadFile] = File(...)):
    """
    Uploads one or more PDF documents.
    The documents are processed to extract text, which is then chunked,
    embedded, and stored in a FAISS vector store for later retrieval.
    """
    global vector_store
    if not embedding_model:
        raise HTTPException(status_code=500, detail="Embedding model is not initialized. Cannot process documents.")

    processed_files_count = 0
    total_chunks_generated_for_session = 0
    all_langchain_documents: List[LangchainDocument] = []

    for file in files:
        if not file.filename:
            print("Received a file without a filename. Skipping.")
            continue # Skip if no filename

        if not file.filename.lower().endswith(".pdf"):
            print(f"Skipping non-PDF file: {file.filename}")
            # Optionally, you could raise an HTTPException for non-PDFs
            # await file.close() # Ensure file is closed
            continue

        temp_file_path = os.path.join(UPLOAD_DIR, file.filename)

        try:
            # Save the uploaded file temporarily to disk for pypdf to read
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            print(f"Temporarily saved {file.filename} to {temp_file_path}")

            # Extract text using pypdf
            print(f"Processing document: {file.filename}...")
            raw_text = extract_text_from_pdf(temp_file_path)

            if not raw_text:
                print(f"No text extracted from {file.filename}. It might be an image-based PDF, empty, or password-protected.")
                continue # Skip if no text could be extracted

            # Chunk the extracted text
            text_chunks = text_splitter.split_text(raw_text)
            if not text_chunks:
                print(f"No chunks generated for {file.filename} after splitting. Text might be too short.")
                continue

            # Create Langchain Document objects for each chunk, including metadata
            for chunk in text_chunks:
                doc = LangchainDocument(
                    page_content=chunk,
                    metadata={"source_filename": file.filename} # Store filename as metadata
                )
                all_langchain_documents.append(doc)

            total_chunks_generated_for_session += len(text_chunks)
            processed_files_count += 1
            print(f"Successfully processed and chunked {file.filename}. Chunks created: {len(text_chunks)}")

        except Exception as e:
            print(f"Failed to process file {file.filename}: {e}")
            # Consider how to report this to the client if needed (e.g., partial success response)
        finally:
            # Clean up the temporarily saved file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"Cleaned up temporary file: {temp_file_path}")
            # Ensure the UploadFile object is closed
            await file.close()

    if not all_langchain_documents:
        if processed_files_count == 0 and len(files) > 0:
             raise HTTPException(status_code=400, detail="No PDF files provided were valid or processable.")
        return DocumentUploadResponse(
            message="No new documents were suitable for indexing or no text could be extracted.",
            documents_indexed=0,
            total_chunks_generated=0
        )

    # Update or create the FAISS index
    try:
        if vector_store is None:
            print(f"Creating new FAISS index with {len(all_langchain_documents)} document chunks.")
            vector_store = FAISS.from_documents(all_langchain_documents, embedding_model)
        else:
            print(f"Adding {len(all_langchain_documents)} new document chunks to existing FAISS index.")
            vector_store.add_documents(all_langchain_documents)

        save_vector_store() # Persist the updated index to disk
    except Exception as e:
        print(f"Error creating or updating FAISS index: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create or update vector store: {str(e)}")

    return DocumentUploadResponse(
        message=f"Documents processed successfully. {processed_files_count} PDF(s) indexed.",
        documents_indexed=processed_files_count,
        total_chunks_generated=total_chunks_generated_for_session
    )


@app.post("/question", response_model=AnswerResponse)
async def ask_question_endpoint(request: QuestionRequest):
    """
    Receives a question, retrieves relevant context from the indexed documents
    using FAISS, and uses Groq's LLM to generate an answer.
    """
    global vector_store
    if vector_store is None:
        raise HTTPException(status_code=400, detail="No documents have been indexed. Please upload documents using the /documents endpoint first.")

    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="Groq API key (GROQ_API_KEY) is not configured on the server. LLM functionality is unavailable.")

    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Initialize the Groq LLM
        # Available models: "mixtral-8x7b-32768", "llama3-70b-8192", "llama3-8b-8192", "gemma-7b-it"
        llm = ChatGroq(
            temperature=0.1, # Lower temperature for more factual answers
            groq_api_key=GROQ_API_KEY,
            model_name="mistral-saba-24b" # Or choose another model
        )

        # Define a prompt template for question answering
        # This template guides the LLM to use the provided context.
        prompt_template_str = """
        You are an AI assistant specialized in answering questions based on provided documents.
        Use ONLY the following pieces of context (document excerpts) to answer the question.
        If the context does not contain the answer, state that you don't know or the information is not available in the provided documents.
        Do not make up information or use external knowledge.
        Keep your answer concise and directly responsive to the question.

        Context:
        {context}

        Question: {question}

        Helpful Answer:
        """
        QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template_str)

        # Create a retriever from the vector store
        # search_kwargs={"k": 3} means retrieve the top 3 most relevant chunks
        retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})

        # Create the RetrievalQA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff", # "stuff" puts all context into one prompt
            retriever=retriever,
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
            return_source_documents=True # Request source documents to be returned
        )

        print(f"Received question: '{request.question}'. Querying RAG chain...")
        # Invoke the chain with the user's question
        # The key for the question input must match what the chain expects (default is "query")
        chain_input = {"query": request.question}
        result = qa_chain.invoke(chain_input)

        answer = result.get("result", "No answer could be generated.").strip()
        
        source_doc_infos: List[SourceDocumentInfo] = []
        if "source_documents" in result and result["source_documents"]:
            for doc in result["source_documents"]:
                source_doc_infos.append(SourceDocumentInfo(
                    source_filename=doc.metadata.get("source_filename", "Unknown source"),
                    content_preview=doc.page_content[:250] + "..." # Provide a preview of the source chunk
                ))
        
        print(f"LLM Answer: {answer}")
        if source_doc_infos:
            print(f"Source documents considered: {[s.source_filename for s in source_doc_infos]}")

        return AnswerResponse(answer=answer, source_documents=source_doc_infos)

    except Exception as e:
        print(f"Error during question answering process: {e}")
        # Consider logging the full traceback for debugging
        # import traceback
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred while processing your question: {str(e)}")


@app.post("/reset_index", status_code=200)
async def reset_index_endpoint():
    """
    Resets the FAISS vector store by deleting the persisted index files
    and clearing the in-memory vector_store variable.
    This is useful for starting fresh without restarting the server.
    """
    global vector_store
    vector_store = None # Clear in-memory store

    # Remove the persisted FAISS index directory and its contents
    if os.path.exists(FAISS_INDEX_PATH):
        try:
            shutil.rmtree(FAISS_INDEX_PATH)
            print(f"Successfully removed FAISS index directory: {FAISS_INDEX_PATH}")
            # Recreate the directory for future use
            os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
            message = "Vector store and persisted index have been reset successfully."
        except Exception as e:
            print(f"Error removing FAISS index directory {FAISS_INDEX_PATH}: {e}")
            # Attempt to recreate directory anyway if it was partially deleted or permissions allow
            os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
            raise HTTPException(status_code=500, detail=f"Could not fully reset vector store directory: {str(e)}")
    else:
        message = "No persisted vector store found to reset. In-memory store cleared."
        # Ensure directory exists for next save
        os.makedirs(FAISS_INDEX_PATH, exist_ok=True)

    print("Vector store has been reset.")
    return {"message": message}

# --- Main execution for Uvicorn (if running this file directly) ---
# This allows you to run the FastAPI app using `python main.py`
# For production, you'd typically use Uvicorn directly: `uvicorn main:app --reload`
if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server using Uvicorn...")
    print(f"API documentation will be available at http://localhost:8000/docs")
    print(f"Make sure GROQ_API_KEY environment variable is set if you haven't already.")
    print(f"FAISS index will be stored in: {os.path.abspath(FAISS_INDEX_PATH)}")
    print(f"Uploaded PDFs will be temporarily stored in: {os.path.abspath(UPLOAD_DIR)}")

    # Uvicorn server configuration
    uvicorn.run(
        "main:app", # Points to the 'app' instance in this 'main.py' file
        host="0.0.0.0", # Listen on all available network interfaces
        port=8000,      # Standard port for development
        reload=True     # Enable auto-reload for development (watches for code changes)
    )
