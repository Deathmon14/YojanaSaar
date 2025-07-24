import os
import json
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import faiss # Import FAISS
import numpy as np # For numerical operations with FAISS

# === Setup ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = "myscheme_api_data.json"
data_file_path = os.path.join(SCRIPT_DIR, DATA_FILE)

# Define paths for FAISS index and metadata
FAISS_INDEX_PATH = os.path.join(SCRIPT_DIR, "faiss_index.bin")
METADATA_PATH = os.path.join(SCRIPT_DIR, "scheme_metadata.json")

# Load data
try:
    with open(data_file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    print(f"[✅] Successfully loaded data from '{DATA_FILE}'. Total items: {len(raw_data)}")
except FileNotFoundError:
    print(f"[❌] Error: '{DATA_FILE}' not found. Please run myscheme_scraper.py first.")
    exit(1)
except json.JSONDecodeError:
    print(f"[❌] Error: Could not decode JSON from '{DATA_FILE}'. Check file integrity.")
    exit(1)
except Exception as e:
    print(f"[❌] An unexpected error occurred while loading data: {e}")
    exit(1)

cleaned_data = []
for item in raw_data:
    # Ensure item is a dictionary and has a valid title
    if isinstance(item, dict) and item.get("title") and item.get("title") != "N/A":
        # Filter out keys with "N/A" or empty values for better document quality
        cleaned_data.append({k: v for k, v in item.items() if v and v != "N/A"})

if not cleaned_data:
    print("[❗] No valid scheme data found after cleaning. Exiting.")
    exit(1)

documents, metadatas = [], []
for i, item in enumerate(cleaned_data):
    # Construct a comprehensive document string for embedding
    doc = "\n".join([
        f"Title: {item.get('title', '')}",
        f"Description: {item.get('description', '')}",
        f"Category: {item.get('category', '')}",
        f"Eligibility: {item.get('eligibility', '')}",
        f"Department: {item.get('department', '')}",
        f"State: {item.get('state', '')}",
        f"Benefits: {item.get('benefits', '')}"
    ])
    documents.append(doc)
    metadatas.append({
        "original_index": i, # Keep original index for debugging if needed
        "title": item.get("title", ""),
        "link": item.get("link", ""),
        "category": item.get("category", ""),
        "department": item.get("department", ""),
        "state": item.get("state", ""),
        "full_document_text": doc # Store the full document text for retrieval
    })

print(f"[⚙️] Prepared {len(documents)} documents for embedding.")

# Embedding Model
MODEL_NAME = "BAAI/bge-base-en-v1.5"
try:
    model = SentenceTransformer(MODEL_NAME)
    print(f"[✅] SentenceTransformer model '{MODEL_NAME}' loaded successfully.")
except Exception as e:
    print(f"[❌] Error loading SentenceTransformer model: {e}")
    exit(1)

print(f"[🚀] Generating embeddings for {len(documents)} documents...")
# Generate embeddings in batches for memory efficiency
batch_size = 100 # Adjust as needed based on your system's memory
all_embeddings = []
for i in tqdm(range(0, len(documents), batch_size), desc="Generating embeddings"):
    batch_docs = documents[i:i + batch_size]
    embeddings = model.encode(batch_docs, convert_to_tensor=False)
    all_embeddings.extend(embeddings)

embeddings_np = np.array(all_embeddings).astype('float32')
dimension = embeddings_np.shape[1]

# === FAISS Indexing ===
print(f"[🛠️] Creating FAISS index with dimension {dimension}...")
# Use IndexFlatL2 for simple L2 (Euclidean) distance similarity search
index = faiss.IndexFlatL2(dimension)

# Add embeddings to the FAISS index
print(f"[➕] Adding {len(embeddings_np)} embeddings to FAISS index...")
index.add(embeddings_np)
print(f"[✅] FAISS index created and populated. Total vectors: {index.ntotal}")

# === Save FAISS Index and Metadata ===
try:
    faiss.write_index(index, FAISS_INDEX_PATH)
    print(f"[💾] FAISS index saved to '{FAISS_INDEX_PATH}'")
except Exception as e:
    print(f"[❌] Error saving FAISS index: {e}")
    exit(1)

try:
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadatas, f, indent=4)
    print(f"[💾] Metadata saved to '{METADATA_PATH}'")
except Exception as e:
    print(f"[❌] Error saving metadata: {e}")
    exit(1)

print("\n[🎉] Phase 1 (Embedding and FAISS Indexing) completed successfully!")