import os
import time
from dotenv import load_dotenv, find_dotenv

import tiktoken
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import Pinecone as PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import pinecone
from pinecone import ServerlessSpec, Pinecone
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


class rag():
    def __init__(self, path, chunk_size, index_name, temperature, gpt_name, embedding_name):
        self.path = path
        self.chunk_size = chunk_size
        self.index_name = index_name
        self.temperature = temperature
        self.gpt_name = gpt_name
        self.embedding_name = embedding_name


    def load_document(self):
        '''Loading documents using langchain for chunking and embedding, files format supported are only pdf and docx'''
        _, extension = os.path.splitext(self.path)

        if extension == '.pdf':
            print(f'\nLoading {self.path}')
            loader = PyPDFLoader(self.path)
        elif extension == '.docx':
            print(f'Loading {self.path}')
            loader = Docx2txtLoader(self.path)
        else:
            print(f'Document format {extension} is not supported!')
            return None

        data = loader.load()    # data: a list of documents as each doc is a page
        return data
    

    def chunk_data(self, doc):   
        '''Splitting the data into multiple chunks, argument= document''' 
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=0)

        chunks = text_splitter.split_documents(doc)
        return chunks
    

    def embedding_cost(self, doc):
        '''Calculating the embedding cost for the openai model
          based on the number of tokens in the document, argument= document'''
        
        tokenizer = tiktoken.encoding_for_model(self.embedding_name)
        total_tokens = sum([len(tokenizer.encode(page.page_content)) for page in doc])
        total_cost = (total_tokens / 1_000_000) * 0.02
        return total_tokens, total_cost


    def insert_or_fetch_embeddings(self, chunks):
        '''Embedding and Uploading to a vector DB (Pinecone), argument= chunks'''
        pc = pinecone.Pinecone()
        embeddings = OpenAIEmbeddings(model=self.embedding_name, dimensions=1536)

        if self.index_name in pc.list_indexes().names():
            print(f'\nIndex {self.index_name} already exist. Loading embeddings ...', end='')
            vector_store = PineconeVectorStore.from_existing_index(self.index_name, embeddings)
            print('Loaded successfully!')
        else:
            print(f'\nCreating index {self.index_name} and embeddings ...', end='')
            pc.create_index(
                name=self.index_name,
                dimension=1536,
                metric='cosine',
                spec=ServerlessSpec(cloud='aws', region='us-east-1')
            )
            vector_store = PineconeVectorStore.from_documents(chunks, embeddings, index_name=self.index_name)
            print('Index created and embeddings loaded successfully!')
        return vector_store
        

    def delete_pinecone_index(self):
        '''Deleting the index in the vector DB'''
        pc = Pinecone()
    
        print(f'Deleting index {self.index_name} ...', end='')
        pc.delete_index(self.index_name)
        print('Index is deleted!')


    def initializing_chain(self, vector_store):
        '''Initialize the chain which include the retriever 
        along with the memory and chat templates, argument= vector_store'''
        llm = ChatOpenAI(model_name=self.gpt_name, temperature=self.temperature)
        retriever = vector_store.as_retriever(search_type='similarity', search_kwargs={'k': 5})

        system_template = '''
        Uses the following pieces of context to answer the user's question,
        I will append the chat history to the user prompt so no need to restate it again in the answer,
        and answer the questions very breifly and accurately
        --------------------------
        Context: ```{context}```
        '''

        user_template = '''
        Question: ```{question}``` 
        Chat History: ```{chat_history}```
        '''

        messages = [
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(user_template)]

        qa_prompt = ChatPromptTemplate.from_messages(messages)

        crc = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            chain_type='stuff',
            combine_docs_chain_kwargs={'prompt': qa_prompt},
            verbose=False)
        return crc
    

    def ask_question(self, chain):
        '''the actual conversational function for asking and answering, argument= chain'''
        i = 1
        chat_history = []
        print('\nStarting the Conversation ---> Q/q for Exiting.')
        while True:
            q = input(f'Question #{i}: ')
            i+=1
            if q.lower() == 'q':
                print('Existing ... bye bye!')
                time.sleep(2)
                break

            answer = chain.invoke({"question": q, "chat_history": chat_history})
            print(f'\nAnswer: {answer["answer"]}')
            print(f'\n {"-" * 150} \n')

            # appending the chat history for future questions
            chat_history.append((q, answer["answer"]))
    


if __name__== "__main__":
    # Loading the API keys
    load_dotenv(find_dotenv(), override=True)
    
    # parameters
    path='Abdulaziz_AlTayar_Resume.pdf'
    chunk_size=256
    index_name='langchain'
    temperature=0
    gpt_name='gpt-4-turbo-preview'
    embedding_name='text-embedding-3-small'

    rag = rag(path, chunk_size, index_name, temperature, gpt_name, embedding_name)

    doc = rag.load_document()
    print(f'\nNumber of pages for doc: {len(doc)}')

    total_tokens, total_cost = rag.embedding_cost(doc)
    print(f'\nThe total tokens: {total_tokens}\n\nThe total cost for embeddings (USD): {total_cost}')

    chunks = rag.chunk_data(doc)
    print(f'\nNumber of chunks in Vector DB: {len(chunks)}')

    vector_store = rag.insert_or_fetch_embeddings(chunks)
    crc = rag.initializing_chain(vector_store)

    rag.ask_question(crc)


