from langchain_openai import OpenAI, OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from langchain_community.vectorstores import Pinecone
from langchain.chains.question_answering import load_qa_chain
from pinecone import Pinecone
import os

# Environment variable validation
if not os.getenv("PINECONE_KEY") or not os.getenv("PINECONE_INDEX_HOST") or not os.getenv("OPEN_AI_KEY"):
    raise ValueError("PINECONE_KEY, PINECONE_INDEX_HOST, or OPEN_AI_KEY environment variable not set")

# Set API keys
pinecone_key = os.getenv("PINECONE_KEY")
index_host = os.getenv("PINECONE_INDEX_HOST")
openai_api_key = os.getenv("OPEN_AI_KEY")

# Initialize Pinecone client
pc = Pinecone(api_key=pinecone_key)
index = pc.Index(host=index_host)

# Function to load a document
def load_document(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            raw_content = f.read()
        if not raw_content.strip():
            print(f"Error: File {file} is empty or contains only whitespace.")
            return ""
        return raw_content
    except Exception as e:
        print(f"Error loading document: {e}")
        return ""

# Function to process and store documents
def process_and_store(file, namespace="default"):
    data = load_document(file)
    if not data.strip():
        print("File content is empty or invalid.")
        return

    document = Document(page_content=data, metadata={"file_name": file})
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents([document])

    print(f"Processing file: {file}")
    print(f"Number of chunks created: {len(chunks)}")

    if not chunks:
        print("No chunks were created. Ensure the file has sufficient content.")
        return

    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)

    for i, chunk in enumerate(chunks):
        chunk_id = f"{file}_chunk_{i}"
        vector = embeddings.embed_query(chunk.page_content)
        metadata = {"file_name": file, "content": chunk.page_content}

        index.upsert(vectors=[(chunk_id, vector, metadata)], namespace=namespace)
        print(f"Upserted chunk {i + 1}/{len(chunks)}")

# Function to search and answer a query
def answer(file, query, namespace="default"):
    process_and_store(file, namespace)

    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
    query_vector = embeddings.embed_query(query)

    search_results = index.query(vector=query_vector, top_k=5, include_metadata=True, namespace=namespace)

    retrieved_docs = [
        Document(page_content=result["metadata"]["content"], metadata={"file_name": result["metadata"]["file_name"]})
        for result in search_results["matches"]
    ]

    # Log the content of the retrieved chunks
    print("Retrieved Chunks Content:", [doc.page_content for doc in retrieved_docs])

    llm = OpenAI(temperature=0, openai_api_key=openai_api_key)
    chain = load_qa_chain(llm, chain_type="stuff")

    response = chain.invoke({"input_documents": retrieved_docs, "question": query})
    print("Answer:", response["output_text"])

# Function to clear old entries in Pinecone
def clear_vectors_by_pattern(file_name, namespace="default"):
    try:
        results = index.query(
            filter={"file_name": file_name},
            top_k=1000,
            include_metadata=True,
            namespace=namespace,
        )
        vector_ids = [match["id"] for match in results["matches"]]
        if vector_ids:
            index.delete(ids=vector_ids, namespace=namespace)
            print(f"Deleted {len(vector_ids)} vectors for file: {file_name}")
        else:
            print(f"No vectors found for file: {file_name}")
    except Exception as e:
        print(f"Error clearing vectors: {e}")

# Example usage
if __name__ == "__main__":
    file_path = "C:\\Users\\nabil\\Downloads\\GithubGPT\\semantic_search\\test.txt"
    query = "How would you define what data science is? I want you to base yourself only on the provided context"

    print("File size:", os.path.getsize(file_path))
    answer(file_path, query)
