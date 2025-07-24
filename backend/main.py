# backend/main.py
import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import necessary components for loading models and data
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np # For numerical operations with FAISS
from dotenv import load_dotenv
import google.generativeai as genai
import google.generativeai.types as genai_types # For specific error types

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="YojanaSaar API",
    description="API for Indian Government Schemes RAG System using Gemini and FAISS.",
    version="1.0.0",
)

# --- CORS Middleware ---
origins = [
    "http://localhost:3000",  # React app default port
    "http://127.0.0.1:3000",
    "null",
    # Add your deployed frontend URL here when you deploy
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global variables for loaded assets ---
llm_model = None
embedding_model = None
faiss_index = None
scheme_metadatas = None

# --- Lifespan Events for Loading Models and Data ---
@app.on_event("startup")
async def load_resources():
    global llm_model, embedding_model, faiss_index, scheme_metadatas

    logger.info("[⚙️] Starting application: Loading resources...")
    try:
        embedding_model = SentenceTransformer("BAAI/bge-base-en-v1.5")
        logger.info("[✅] SentenceTransformer model loaded.")
    except Exception as e:
        logger.error(f"[❌] Error loading SentenceTransformer model: {e}")
        raise HTTPException(status_code=500, detail="Failed to load embedding model.")

    try:
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        FAISS_INDEX_PATH = os.path.join(SCRIPT_DIR, "faiss_index.bin")
        METADATA_PATH = os.path.join(SCRIPT_DIR, "scheme_metadata.json")

        faiss_index = faiss.read_index(FAISS_INDEX_PATH)
        logger.info(f"[✅] FAISS index loaded. Total vectors: {faiss_index.ntotal}")

        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            scheme_metadatas = json.load(f)
        logger.info(f"[✅] Metadata loaded. Total items: {len(scheme_metadatas)}")

    except FileNotFoundError:
        logger.error("[❌] Critical: FAISS index or metadata files not found. Run phase1_embedding.py first.")
        raise HTTPException(status_code=500, detail="Required data files not found. Please run phase1_embedding.py.")
    except Exception as e:
        logger.error(f"[❌] Error loading FAISS index or metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load FAISS index or metadata: {e}")

    try:
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not GEMINI_API_KEY:
            logger.error("[❌] GEMINI_API_KEY not found in environment variables.")
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured.")

        genai.configure(api_key=GEMINI_API_KEY)
        llm_model = genai.GenerativeModel("gemini-2.0-flash")
        logger.info("[✅] Gemini GenerativeModel loaded.")
    except Exception as e:
        logger.error(f"[❌] Error loading Gemini GenerativeModel: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load Gemini model: {e}")

    logger.info("[✅] All resources loaded successfully. App ready.")

@app.on_event("shutdown")
async def shutdown_resources():
    logger.info("[👋] Shutting down application.")


# --- Pydantic Models for Request/Response ---
class Message(BaseModel):
    role: str # "user" or "model"
    content: str

class QueryRequest(BaseModel):
    user_query: str
    k: int = 5 # Number of relevant documents to retrieve
    state: Optional[str] = None
    category: Optional[str] = None
    # New: For conversation history
    conversation_history: List[Message] = []

class SchemeDetail(BaseModel):
    title: str
    link: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    state: Optional[str] = None
    full_document_text: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    relevant_schemes: List[SchemeDetail] = []
    # No need for query_id yet, handled by frontend history

# --- Core RAG Logic ---
def get_rag_response(
    user_query: str,
    k: int,
    state_filter: Optional[str],
    category_filter: Optional[str],
    conversation_history: List[Message]
) -> QueryResponse:
    if embedding_model is None or faiss_index is None or scheme_metadatas is None or llm_model is None:
        raise RuntimeError("Core components not loaded. Application is not ready.")

    try:
        query_embedding = embedding_model.encode([user_query], convert_to_tensor=False).astype('float32')
        distances, indices = faiss_index.search(query_embedding, k * 2) # Retrieve more to filter

        retrieved_items = []
        for i in indices[0]:
            if 0 <= i < len(scheme_metadatas):
                retrieved_items.append(scheme_metadatas[i])
            else:
                logger.warning(f"FAISS returned out-of-bounds index: {i}")

        filtered_items = []
        for item_meta in retrieved_items:
            match = True
            if state_filter and item_meta.get("state", "").lower() != state_filter.lower():
                match = False
            if category_filter and item_meta.get("category", "").lower() != category_filter.lower():
                match = False
            if match:
                filtered_items.append(item_meta)

        relevant_items_for_llm = filtered_items[:k]

        if not relevant_items_for_llm:
            logger.info("No relevant documents found after filtering.")
            return QueryResponse(
                answer="I couldn't find any relevant schemes in the database based on your query and filters. Please try rephrasing your question or adjusting the filters.",
                relevant_schemes=[]
            )

        context_items = []
        response_scheme_details: List[SchemeDetail] = []
        for item_meta in relevant_items_for_llm:
            context_items.append(
                f"### Scheme: {item_meta.get('title', 'N/A')}\n" # Using Markdown heading
                f"Description: {item_meta.get('full_document_text', 'N/A')}\n"
                f"Category: {item_meta.get('category', 'N/A')}\n"
                f"Department: {item_meta.get('department', 'N/A')}\n"
                f"State: {item_meta.get('state', 'N/A')}\n"
                f"Link: {item_meta.get('link', 'N/A')}"
            )
            response_scheme_details.append(
                SchemeDetail(
                    title=item_meta.get("title", "N/A"),
                    link=item_meta.get("link"),
                    category=item_meta.get("category"),
                    department=item_meta.get("department"),
                    state=item_meta.get("state"),
                    full_document_text=item_meta.get("full_document_text")
                )
            )

        context = "\n\n---\n\n".join(context_items)

        # Build the conversation parts for Gemini
        # Gemini expects a specific format for history, e.g., [{"role": "user", "parts": ["text"]}, {"role": "model", "parts": ["text"]}]
        gemini_history_parts = []
        for msg in conversation_history:
            gemini_history_parts.append({"role": msg.role, "parts": [msg.content]})

        # New prompt for Markdown output and incorporating history
        prompt_parts = [
            {"role": "user", "parts": ["""You are YojanaSaar, a kind and knowledgeable AI advisor that helps Indian citizens discover relevant government schemes.

            Based *only* on the schemes provided in the context below, suggest helpful options to the user. Explain why each scheme applies to them (e.g., for farmers, students, by state, etc).
            Format your answer using Markdown, including headings for each suggested scheme, bullet points for details, and bold text where appropriate.

            If no relevant information is found in the provided context that directly answers the user's question, politely explain that and suggest what kind of details the user can provide to get better help. Do not make up information.

            ### Context:
            """ + context]},
            # Your conversation history goes here
            *gemini_history_parts,
            {"role": "user", "parts": [f"### Current Question:\n{user_query}"]},
            {"role": "model", "parts": ["### Answer:"]} # To guide Gemini to start its answer with this heading
        ]

        logger.info(f"Sending prompt to Gemini for query: {user_query}")
        # Use generate_content with parts for history
        answer_response = llm_model.generate_content(prompt_parts)
        response_text = answer_response.text

        logger.info("Gemini response received.")
        return QueryResponse(answer=response_text, relevant_schemes=response_scheme_details)

    except genai_types.BlockedPromptException as e:
        logger.error(f"[❌] Gemini API Error (Blocked Prompt): {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"The query was blocked by the safety system. This might be due to safety concerns with the prompt. Please try rephrasing your question.")
    except genai_types.APIError as e:
        logger.error(f"[❌] Gemini API Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error communicating with the Gemini API. Please try again later. Details: {e}")
    except Exception as e:
        logger.error(f"[❌] An unexpected error occurred during the query process for '{user_query}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during the query process: {e}")


# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": "Welcome to YojanaSaar API! Use /query to get scheme information."}

@app.get("/health")
async def health_check():
    """Checks the health of the application and its dependencies."""
    status = {"status": "ok", "components": {}}

    status["components"]["embedding_model"] = "loaded" if embedding_model else "failed"
    status["components"]["faiss_index"] = "loaded" if faiss_index else "failed"
    status["components"]["faiss_index_count"] = faiss_index.ntotal if faiss_index else 0
    status["components"]["scheme_metadatas"] = "loaded" if scheme_metadatas else "failed"
    status["components"]["scheme_metadata_count"] = len(scheme_metadatas) if scheme_metadatas else 0
    status["components"]["gemini_llm"] = "loaded" if llm_model else "failed"

    if all(comp == "loaded" for comp in status["components"].values()):
        status["status"] = "ok"
        status_code = 200
    else:
        status["status"] = "degraded"
        status_code = 503

    return JSONResponse(content=status, status_code=status_code)

@app.post("/query", response_model=QueryResponse)
async def query_schemes(request: QueryRequest):
    """
    Accepts a user query, optional filters, and conversation history,
    then returns relevant Indian government schemes using RAG with Markdown formatting.
    """
    logger.info(f"Received query: '{request.user_query}' with k={request.k}, state='{request.state}', category='{request.category}'. History length: {len(request.conversation_history)}")
    response = get_rag_response(
        request.user_query,
        request.k,
        request.state,
        request.category,
        request.conversation_history # Pass the conversation history
    )
    return response