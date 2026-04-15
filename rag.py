import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from langchain_community.document_loaders import DirectoryLoader, Docx2txtLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

class RAGSystem:
    def __init__(self, data_dir='data', db_path='vector_db'):
        self.embeddings = OpenAIEmbeddings()
        self.db_path = db_path
        self.data_dir = data_dir
        
        # Check if vector store exists
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            print("Loading existing vector store...")
            self.vectorstore = FAISS.load_local(self.db_path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            print("Creating new vector store...")
            self._initialize_vectorstore()
        
        # Create QA chain
        self._create_qa_chain()
    
    def _initialize_vectorstore(self):
        """Initialize vector store from documents."""
        # Load documents
        loader = DirectoryLoader(self.data_dir, glob="*.docx", loader_cls=Docx2txtLoader)
        documents = loader.load()
        
        if not documents:
            raise ValueError(f"No DOCX documents found in {self.data_dir}")
        
        # Split documents
        text_splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=50)
        docs = text_splitter.split_documents(documents)
        
        # Create vector store
        self.vectorstore = FAISS.from_documents(docs, self.embeddings)
        
        # Save to disk
        self.vectorstore.save_local(self.db_path)
        print(f"Vector store saved to {self.db_path}")
    
    def _create_qa_chain(self):
        """Create the QA chain."""
        # Custom prompt to control hallucinations
        prompt_template = """Context: {context}

Question: {question}

Answer based only on the context. If not in context, say "I don't know"."""
        
        prompt = PromptTemplate.from_template(prompt_template)
        llm = OpenAI(model="gpt-4o-mini")
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 2})
        
        self.qa_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
    
    def query(self, query):
        """Query the RAG system."""
        if self.qa_chain is None:
            raise ValueError("QA chain not initialized.")
        return self.qa_chain.invoke(query)

# def main():
#     try:
#         rag = RAGSystem()
#         print("RAG system initialized successfully.")
#         query = "What is chronic disease?"
#         result = rag.query(query)
#         print("Query:", query)
#         print("Answer:", result)
#     except Exception as e:
#         print(f"Error: {e}")


# if __name__ == "__main__":
#     main()