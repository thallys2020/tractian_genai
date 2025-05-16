import os
import shutil # For cleaning up storage and directories
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# PDF processing
import pypdf # PyPDF2 is now pypdf

# LangChain components
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document as LangchainDocument
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Load Groq API key from environment variable
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("Warning: GROQ_API_KEY environment variable not set. LLM functionality will fail.")
    # In a production scenario, you might want to raise an error or prevent startup.

# Paths for storing data
FAISS_INDEX_PATH = "faiss_index_store"
UPLOAD_DIR = "uploaded_pdfs" # Temporary storage for uploaded files

# Ensure directories exist
os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Global Variables / State ---
# This holds the loaded FAISS vector store.
# In a multi-worker setup, this in-memory approach would need refinement (e.g., shared cache, DB).
vector_store: Optional[FAISS] = None

# Initialize embedding model (using a popular sentence transformer)
# This model runs locally (downloads on first use if not cached).
try:
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
except Exception as e:
    print(f"Error initializing HuggingFaceEmbeddings: {e}. Ensure sentence-transformers is installed and model is accessible.")
    embedding_model = None # Handle potential initialization failure

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # Max size of a chunk
    chunk_overlap=200, # Overlap between chunks to maintain context
    length_function=len
)

def load_vector_store():
    """Loads the FAISS vector store from disk if it exists."""
    global vector_store
    if not embedding_model:
        print("Embedding model not initialized. Cannot load vector store.")
        vector_store = None
        return

    index_file_path = os.path.join(FAISS_INDEX_PATH, "index.faiss")
    if os.path.exists(index_file_path):
        try:
            # allow_dangerous_deserialization is needed for FAISS with HuggingFaceEmbeddings
            vector_store = FAISS.load_local(
                FAISS_INDEX_PATH,
                embedding_model,
                allow_dangerous_deserialization=True
            )
            print(f"FAISS index loaded successfully from {FAISS_INDEX_PATH}.")
        except Exception as e:
            print(f"Error loading FAISS index from {FAISS_INDEX_PATH}: {e}. A new index will be created if documents are uploaded.")
            vector_store = None # Ensure it's reset if loading fails
    else:
        print(f"No FAISS index found at {FAISS_INDEX_PATH}. A new index will be created upon document upload.")
        vector_store = None

def save_vector_store():
    """Saves the FAISS vector store to disk."""
    global vector_store
    if vector_store:
        try:
            vector_store.save_local(FAISS_INDEX_PATH)
            print(f"FAISS index saved successfully to {FAISS_INDEX_PATH}.")
        except Exception as e:
            print(f"Error saving FAISS index to {FAISS_INDEX_PATH}: {e}")

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text from a PDF file using pypdf.
    IMPORTANT: pypdf does NOT perform OCR. For scanned/image-based PDFs,
    text extraction will be limited or yield no results.
    The user requirement "OCR Py2PDF" is interpreted as using pypdf for PDF handling.
    A dedicated OCR tool (e.g., Tesseract) would be needed for image-based PDFs.
    """
    full_text = ""
    try:
        reader = pypdf.PdfReader(pdf_path)
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
            else:
                print(f"No text extracted from page {i+1} of {os.path.basename(pdf_path)}. It might be an image.")
    except Exception as e:
        print(f"Error reading PDF {os.path.basename(pdf_path)} at path {pdf_path}: {e}")
        # Depending on desired behavior, you might raise an exception here
        # or return the text extracted so far.
    return full_text.strip()

# --- Pydantic Models for Request/Response ---
class DocumentUploadResponse(BaseModel):
    message: str
    documents_indexed: int
    total_chunks_generated: int # Renamed for clarity from "total_chunks"

class QuestionRequest(BaseModel):
    question: str

class SourceDocumentInfo(BaseModel):
    source_filename: str
    content_preview: str

class AnswerResponse(BaseModel):
    answer: str
    source_documents: Optional[List[SourceDocumentInfo]] = None