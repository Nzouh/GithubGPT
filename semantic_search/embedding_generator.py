from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI

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
index_host = os.getenv("PINECONE_INDEX_HOST").rstrip("/").strip()
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

def process_and_store_all(files, namespace="default"):
    """
    Process and store embeddings for all files in the namespace, avoiding duplication.

    :param files: List of tuples containing (file_path, content).
    :param namespace: Namespace in Pinecone for storing embeddings.
    """
    try:
        # Get existing file names from Pinecone metadata
        existing_files = set()
        index_stats = index.describe_index_stats(namespace=namespace)
        for vector_id, vector_metadata in index_stats.get("namespaces", {}).get(namespace, {}).get("vectors", {}).items():
            if "file_name" in vector_metadata.get("metadata", {}):
                existing_files.add(vector_metadata["metadata"]["file_name"])

        # Process files
        for file_path, content in files:
            if not content.strip():
                print(f"Skipping empty or invalid file: {file_path}")
                continue

            # Check if embeddings for the file already exist in Pinecone
            if file_path in existing_files:
                print(f"Embeddings already exist for file: {file_path}. Skipping.")
                continue

            # Process and store new embeddings
            document = Document(page_content=content, metadata={"file_name": file_path})
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = splitter.split_documents([document])

            print(f"Processing file: {file_path}")
            print(f"Number of chunks created: {len(chunks)}")

            if not chunks:
                print(f"No chunks created for {file_path}. Skipping.")
                continue

            embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)

            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_path}_chunk_{i}"
                vector = embeddings.embed_query(chunk.page_content)
                metadata = {"file_name": file_path, "content": chunk.page_content}

                # Store in Pinecone
                index.upsert(vectors=[(chunk_id, vector, metadata)], namespace=namespace)
                print(f"Upserted chunk {i + 1}/{len(chunks)} into Pinecone.")

    except Exception as e:
        print(f"Error processing files: {e}")




def answer(query, namespace="default"):
    """
    Retrieve relevant embeddings from Pinecone and answer the query.

    :param query: The query string to answer.
    :param namespace: Namespace in Pinecone for retrieving embeddings.
    :return: AI-generated answer.
    """
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
    query_vector = embeddings.embed_query(query)

    print(f"Querying Pinecone in namespace: {namespace}")
    search_results = index.query(vector=query_vector, top_k=5, include_metadata=True, namespace=namespace)

    print("Pinecone Query Results:", search_results)

    if not search_results or not search_results.get("matches"):
        return "No relevant information found in the repository."

    retrieved_docs = [
        Document(page_content=result["metadata"]["content"], metadata={"file_name": result["metadata"]["file_name"]})
        for result in search_results["matches"]
    ]

    llm = OpenAI(temperature=0, openai_api_key=openai_api_key)
    chain = load_qa_chain(llm, chain_type="stuff")

    response = chain.invoke({"input_documents": retrieved_docs, "question": query})
    print("Generated Answer:", response["output_text"])
    return response["output_text"]
