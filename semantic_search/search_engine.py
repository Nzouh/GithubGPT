import os
import ast
import chardet  # To detect file encoding
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Pinecone
from pinecone import Pinecone, ServerlessSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import OpenAI
from langchain.chains.question_answering import load_qa_chain

# Initialize Pinecone
pinecone_key = os.getenv("PINECONE_KEY")
pc = Pinecone(api_key=pinecone_key)
index_name = "my-pinecone-index"
index_host = os.getenv("PINECONE_INDEX_HOST")

# Check if the index exists, create if not
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-west-2")
    )

index = pc.Index(index_name)

# Initialize OpenAI embeddings
openai_api_key = os.getenv("OPEN_AI_KEY")
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)

def parse_python_file(file_path):
    """
    Parse a Python file into its functions and classes.

    :param file_path: Path to the Python file.
    :return: List of dictionaries containing function/class name, start/end lines, and code content.
    """
    with open(file_path, "rb") as f:
        raw_data = f.read()

    # Detect file encoding
    detected_encoding = chardet.detect(raw_data).get("encoding", "utf-8")

    try:
        # Decode using the detected encoding
        code = raw_data.decode(detected_encoding)

        tree = ast.parse(code)
        parsed_blocks = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                block_name = node.name
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, "end_lineno") else None
                block_content = "\n".join(code.splitlines()[start_line - 1:end_line])
                parsed_blocks.append({
                    "name": block_name,
                    "type": "function" if isinstance(node, ast.FunctionDef) else "class",
                    "start_line": start_line,
                    "end_line": end_line,
                    "content": block_content
                })
        return parsed_blocks
    except (UnicodeDecodeError, SyntaxError) as e:
        print(f"Error parsing {file_path}: {e}")
        return []

def process_and_index_file(file_path, content, namespace="default"):
    """
    Process and index the content of a file into Pinecone.

    :param file_path: Path to the file.
    :param content: Content of the file.
    :param namespace: Namespace for storing embeddings in Pinecone.
    """
    if not content.strip():
        print(f"Skipping empty or invalid file: {file_path}")
        return

    # Use RecursiveCharacterTextSplitter to chunk the file content
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)

    for i, chunk in enumerate(chunks):
        chunk_id = f"{file_path}_chunk_{i}"
        vector = embeddings.embed_query(chunk)
        metadata = {
            "file_path": file_path,
            "chunk_index": i,
            "content": chunk
        }
        index.upsert(vectors=[(chunk_id, vector, metadata)], namespace=namespace)
        print(f"Indexed chunk {i + 1}/{len(chunks)} from file {file_path}")

def search_code(query, namespace="default", top_k=5):
    """
    Search for file chunks matching a query.

    :param query: The search query.
    :param namespace: Pinecone namespace for retrieving embeddings.
    :param top_k: Number of top matches to retrieve.
    :return: List of matching chunks with metadata.
    """
    query_vector = embeddings.embed_query(query)
    results = index.query(vector=query_vector, top_k=top_k, include_metadata=True, namespace=namespace)

    matches = []
    for match in results.get("matches", []):
        metadata = match["metadata"]
        matches.append({
            "file_path": metadata["file_path"],
            "chunk_index": metadata.get("chunk_index"),
            "content": metadata.get("content")
        })
    return matches

def combined_query(query, namespace="default", top_k=5):
    """
    Combine results from all indexed files and search engine.

    :param query: The query string.
    :param namespace: Namespace for embeddings.
    :param top_k: Number of top matches to retrieve.
    :return: Combined response from embeddings and search engine.
    """
    # Retrieve semantic results from indexed files
    query_vector = embeddings.embed_query(query)

    print(f"Querying Pinecone in namespace: {namespace}")
    embedding_results = index.query(vector=query_vector, top_k=top_k, include_metadata=True, namespace=namespace)

    embedding_matches = [
        {
            "file_path": result["metadata"].get("file_path"),
            "content": result["metadata"].get("content"),
            "source": "embedding_generator"
        }
        for result in embedding_results.get("matches", [])
    ]

    return embedding_matches

def answer(query, namespace="default", top_k=10):
    """
    Retrieve relevant embeddings from Pinecone and generate an AI-driven answer.

    :param query: The query string to answer.
    :param namespace: Namespace for embeddings.
    :param top_k: Number of top matches to retrieve.
    :return: AI-generated answer.
    """
    try:
        combined_results = combined_query(query, namespace=namespace, top_k=top_k)

        if not combined_results:
            return "No relevant information found in the repository."

        # Prepare retrieved documents for LangChain
        retrieved_docs = [
            Document(page_content=result["content"], metadata=result)
            for result in combined_results
            if result.get("content")
        ]

        if not retrieved_docs:
            return "No relevant content available for the query."

        # Generate the AI-driven response
        llm = OpenAI(temperature=0, openai_api_key=openai_api_key)
        chain = load_qa_chain(llm, chain_type="stuff")

        response = chain.invoke({"input_documents": retrieved_docs, "question": query})
        return response["output_text"]

    except Exception as e:
        print(f"Error generating answer: {e}")
        return "Error occurred while processing the query."

if __name__ == "__main__":
    directory = "./"  # Path to your repository
    exclude_dirs = {"venv", "__pycache__"}  # Directories to exclude

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            process_and_index_file(file_path, content)

    query = "Where is the function that handles authentication?"
    results = combined_query(query)
    for result in results:
        print(f"Source: {result['source']}\nFile: {result['file_path']}\nContent: {result['content']}\n")




def get_pinecone_index():
    """
    Initialize and return the Pinecone index.
    """
    pinecone_key = os.getenv("PINECONE_KEY")
    pc = Pinecone(api_key=pinecone_key)
    index_name = "my-pinecone-index"

    # Check if the index exists, create if not
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-west-2")
        )

    return pc.Index(index_name)

def clear_namespace(index, namespace):
    """
    Clear all vectors in a specific namespace.
    
    :param index: Pinecone index instance.
    :param namespace: Namespace to clear.
    """
    try:
        index = pc.Index(host=index_host)
        index.delete(delete_all=True, namespace=namespace)
        print(f"Cleared existing data in namespace: {namespace}")
    except Exception as e:
        print(f"Error clearing namespace '{namespace}': {e}")
