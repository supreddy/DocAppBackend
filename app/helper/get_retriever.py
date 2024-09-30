from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import chromadb
load_dotenv()
from db.db import get_LC_chroma_client
from config import DB_NAME


 
def get_retriever(num_of_results=20):
    try:
        LC_chroma_client=get_LC_chroma_client()
        collection = LC_chroma_client.get()
        print("---from api")
        
        if collection:
            retriever = LC_chroma_client.as_retriever( search_kwargs={"k": num_of_results})
            return retriever
    except Exception as e:
        print('Error retrieving documents:', e)

# Example usage:
# retriever = await get_retriever()
# relevant_docs = await retriever.get_relevant_documents(question)


def get_custom_retriever(top_k):
    """
    Initializes and returns a retriever configured to fetch the top K relevant documents.

    :param top_k: The number of top documents to retrieve.
    :return: A retriever object.
    """
    class CustomRetriever:
        def get_relevant_documents(self, query):
            # Implementation: Replace with actual retrieval logic
            # Here, you might connect to a search engine, a database, or some other
            # data source to retrieve documents relevant to the query.
            
            # For example purposes, returning mock data
            return [{"doc_id": i, "page_content": f"Relevant content {i} for {query}"} for i in range(1, top_k + 1)]
    
    # Return an instance of the CustomRetriever class
    return CustomRetriever()