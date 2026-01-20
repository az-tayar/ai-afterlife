# 📘 RAG Q&A Application (LangChain + Pinecone + OpenAI)

This project implements a Retrieval-Augmented Generation (RAG) system
that allows you to load a document, store its embeddings in Pinecone,
and ask conversational questions grounded in the document's content. The
goal is to provide accurate, context-aware answers using LangChain's
conversational retrieval pipeline.

## 🔄 Pipeline Overview

The application follows a complete RAG workflow:

1.  **Load Document** (PDF or DOCX)\
2.  **Chunk the Document** using `RecursiveCharacterTextSplitter`\
3.  **Create or Fetch Index** in Pinecone\
4.  **Insert or Retrieve Embeddings**\
5.  **Initialize Conversational Retrieval Chain**\
6.  **Interactive Q&A Session** using chat history and GPT

## 🛠️ Setup Instructions

### 1. Install Dependencies

    pip install -r requirements.txt

### 2. Add API Keys

Create a `.env` file in the project directory:

    OPENAI_API_KEY=your_openai_key
    PINECONE_API_KEY=your_pinecone_key

### 3. Add Your Document

Place your `.pdf` or `.docx` file inside the project folder.

### 4. Run the Script

    python rag_query_engine.py

## ⚙️ Adjustable Parameters

Modify these values in the `__main__` section to control the behavior of
the system:

    path = 'your_document.pdf'                # Document location
    chunk_size = 256                          # Chunk size for splitting
    index_name = 'langchain'                  # Pinecone index name
    temperature = 0                           # LLM creativity level
    gpt_name = 'gpt-4-turbo-preview'          # LLM for Q&A
    embedding_name = 'text-embedding-3-small' # Embedding model

## ▶️ Usage

When the program runs:

    Starting the Conversation ---> Q/q for Exiting.
    Question #1:

-   Type any question related to your document\
-   The model retrieves relevant context and answers\
-   Type **q** to exit the conversation

## 📌 Notes

-   The script automatically creates a Pinecone index if it does not
    exist\
-   If the index already exists, it loads existing embeddings\
-   You can delete the index by calling the `delete_pinecone_index()`
    function if needed
