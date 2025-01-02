from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.llms import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.vectorstores import Pinecone as LangChainPinecone
from pinecone import Pinecone, ServerlessSpec  # Updated Pinecone imports
from langchain.chains.question_answering import load_qa_chain
import os

# Environment variable validation
if not os.getenv("PINECONE_KEY") or not os.getenv("OPEN_AI_KEY"):
    raise ValueError("PINECONE_KEY or OPEN_AI_KEY environment variable not set")

# Set API keys
pinecone_key = os.getenv("PINECONE_KEY")
openai_api_key = os.getenv("OPEN_AI_KEY")

# Initialize Pinecone environment
pc = Pinecone(api_key=pinecone_key)
index_name = "my-pinecone-index"  # Replace with your actual index name

# Check if the index exists, create if not
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=1536,  # Update based on your embedding model
        metric="cosine",  # Use "cosine", "dotproduct", or "euclidean"
        spec=ServerlessSpec(cloud="aws", region="us-west-2")  # Replace with your cloud and region
    )

# Connect to the index
index = pc.Index(index_name)

def process_and_store_all(files, namespace="default"):
    """
    Process and store embeddings for all files in the namespace, including the full repository structure.

    :param files: List of tuples containing (file_path, content).
    :param namespace: Namespace in Pinecone for storing embeddings.
    """
    try:
        # Create a document representing the entire repository structure
        repo_structure = "\n".join([file[0] for file in files])  # Combine all file paths
        repo_document = Document(page_content=repo_structure, metadata={"type": "repo_structure"})

        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
        vector = embeddings.embed_query(repo_structure)

        # Store repository structure in Pinecone
        repo_vector_id = "repository_structure"
        index.upsert(vectors=[(repo_vector_id, vector, {"type": "repo_structure", "content": repo_structure})], namespace=namespace)
        print("Upserted repository structure into Pinecone.")

        # Process and store individual files
        for file_path, content in files:
            if not content.strip():
                print(f"Skipping empty or invalid file: {file_path}")
                continue

            # Embed and store the file name
            file_name = os.path.basename(file_path)
            file_vector = embeddings.embed_query(file_name)
            index.upsert(vectors=[(file_name, file_vector, {"type": "file_name", "file_name": file_name})], namespace=namespace)
            print(f"Upserted file name {file_name} into Pinecone.")

            # Process and store file content in chunks
            document = Document(page_content=content, metadata={"file_name": file_name, "file_path": file_path})
            splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
            chunks = splitter.split_documents([document])

            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_name}_chunk_{i}"
                chunk_vector = embeddings.embed_query(chunk.page_content)
                metadata = {
                    "type": "file_content",
                    "file_name": file_name,
                    "file_path": file_path,
                    "content": chunk.page_content
                }
                index.upsert(vectors=[(chunk_id, chunk_vector, metadata)], namespace=namespace)
                print(f"Upserted chunk {i + 1}/{len(chunks)} for file {file_name}.")

    except Exception as e:
        print(f"Error processing files: {e}")

def answer(query, namespace="default"):
    """
    Retrieve relevant embeddings from Pinecone and answer the query.

    :param query: The query string to answer.
    :param namespace: Namespace in Pinecone for retrieving embeddings.
    :return: AI-generated answer.
    """
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
        query_vector = embeddings.embed_query(query)

        print(f"Querying Pinecone in namespace: {namespace}")
        search_results = index.query(vector=query_vector, top_k=10, include_metadata=True, namespace=namespace)

        print("Pinecone Query Results:", search_results)

        if not search_results or not search_results.get("matches"):
            return "No relevant information found in the repository."

        # Handle queries about repository structure or files
        if "files" in query.lower() or "structure" in query.lower():
            file_list = list({
                result["metadata"].get("file_name", result["metadata"].get("content"))
                for result in search_results["matches"]
                if result["metadata"].get("type") in ["repo_structure", "file_name"]
            })
            return f"The repository contains the following files: {', '.join(file_list)}"

        # Combine content from multiple relevant chunks
        retrieved_docs = [
            Document(page_content=result["metadata"]["content"], metadata=result["metadata"])
            for result in search_results["matches"]
            if result["metadata"].get("type") == "file_content"
        ]

        llm = OpenAI(temperature=0, openai_api_key=openai_api_key)
        chain = load_qa_chain(llm, chain_type="stuff")

        response = chain.invoke({"input_documents": retrieved_docs, "question": query})
        return response["output_text"]

    except Exception as e:
        print(f"Error during query processing: {e}")
        return "Error occurred while processing the query."
