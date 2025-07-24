YojanaSaar is an AI-powered government schemes discovery platform forIndian citizens.

  Project Overview

  YojanaSaar AI helps users find relevant Indian government schemes through
   natural language queries and voice interaction.

  Architecture

  Backend (backend/)

  - FastAPI server with CORS support for React frontend
  - RAG (Retrieval-Augmented Generation) pipeline using:
    - FAISS vector database for semantic search
    - SentenceTransformer (BAAI/bge-base-en-v1.5) for embeddings
    - Google Gemini 2.0 Flash LLM for response generation
  - Data Pipeline:
    - myscheme_scraper.py - scrapes MyScheme.gov.in API
    - phase1_embedding.py - creates embeddings and FAISS index
    - phase2_query_pipeline.py - query processing logic

  Frontend (frontend/)

  - React application with modern UI
  - Features:
    - Chat-style conversation interface with avatars
    - Markdown response rendering
    - Voice Assistant - speech-to-text input and text-to-speech output
    - State/category filtering
    - Conversation history with localStorage persistence
    - Responsive scheme cards display

  Key Features

  1. Conversational AI - Chat with context-aware responses
  2. Voice Interface - Ask questions and hear responses
  3. Smart Filtering - Filter by state and category
  4. Scheme Cards - Detailed scheme information display
  5. Persistent History - Saves conversation across sessions

  Tech Stack

  - Backend: FastAPI, FAISS, SentenceTransformers, Google Gemini API
  - Frontend: React 19, Axios, React-Markdown, Web Speech API
  - Data: Government schemes from MyScheme.gov.in

  The system provides an intuitive way for citizens to discover government
  benefits through natural conversation.
