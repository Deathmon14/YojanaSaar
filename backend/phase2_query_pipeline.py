import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
import google.api_core.exceptions
from typing import List, Dict, Any, Optional
import os

print("[🧠] Initializing Phase 2 Pipeline...")

# --- Configuration ---
METADATA_PATH = 'scheme_metadata.json'
FAISS_INDEX_PATH = 'faiss_index.bin'
# --- ENSURE THIS IS THE SAME IN ALL FILES ---
EMBEDDING_MODEL = 'all-MiniLM-L6-v2' 

# --- Load Pre-built Artifacts ---
try:
    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(METADATA_PATH, 'r', encoding='utf-8') as f:
        scheme_metadata = json.load(f)
    model = SentenceTransformer(EMBEDDING_MODEL)
except FileNotFoundError as e:
    print(f"[❌] Error: Could not find file: {e.filename}. Please run phase1_embedding.py first.")
    exit(1)

# --- Configure Gemini API ---
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except Exception as e:
     print(f"[❌] Failed to configure Gemini: {e}")
     exit(1)

def search_schemes(query: str, k: int = 5) -> List[Dict[str, Any]]:
    query_embedding = model.encode([query])
    # Ensure the embedding dimensions match before searching
    assert query_embedding.shape[1] == index.d, f"Embedding dimension mismatch! Query: {query_embedding.shape[1]}, Index: {index.d}"
    distances, indices = index.search(np.array(query_embedding, dtype=np.float32), k)
    
    results = [scheme_metadata[i] for i in indices[0] if i < len(scheme_metadata)]
    return results

def get_rag_response(user_query: str, retrieved_docs: List[Dict[str, Any]], conversation_history: Optional[List[Dict]] = None) -> str:
    context = "\n\n".join([f"Scheme: {doc.get('title', 'N/A')}\nDescription: {doc.get('description', 'N/A')}" for doc in retrieved_docs])
    history_str = "\n".join([f"{entry['role']}: {entry['content']}" for entry in conversation_history]) if conversation_history else ""

    prompt_template = f"""
As 'YojanaSaar AI', your task is to answer user questions about Indian government schemes based *only* on the provided context.

**Instructions:**
1. Analyze the user's question to understand their core need.
2. Carefully examine the provided scheme details in the 'Context' section.
3. **Strictly adhere to the provided context.** Do not use any outside knowledge.
4. If the schemes in the context are relevant, synthesize a helpful answer.
5. **If the schemes do not seem relevant, DO NOT try to force a connection.** Instead, state that you could not find a specific match and politely ask for more details.

### Conversation History:
{history_str}

### Context with Retrieved Schemes:
{context}

### User's Current Question:
{user_query}

### Answer:
"""
    # --- CORRECTED ERROR HANDLING ---
    try:
        llm = genai.GenerativeModel('gemini-1.5-flash')
        response = llm.generate_content(prompt_template)
        return response.text
    except google.api_core.exceptions.GoogleAPICallError as e:
        print(f"[❌] Gemini API Call Error: {e}")
        return "Sorry, I'm having trouble connecting to the AI service right now."
    except Exception as e:
        print(f"[❌] An unexpected error occurred in get_rag_response: {e}")
        return "I'm sorry, but an unexpected error occurred. Please try again."