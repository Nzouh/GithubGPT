from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain.schema import Document
from langchain.vectorstores import Pinecone
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

# Load document
def load_document(file):
    """
    Loads the content of a file into memory using TextLoader.
    """
    try:
        with open(file, "r", encoding="utf-8") as f:
            raw_content = f.read()

        # Use TextLoader to process the file
        loader = TextLoader(file)
        data = loader.load()

        # If data is a list of documents, concatenate their content
        if isinstance(data, list):
            concatenated_content = "\n".join([doc.page_content for doc in data])
        else:
            concatenated_content = data

        return concatenated_content
    except Exception as e:
        print(f"Error loading document: {e}")
        return ""

# Process and store document
def process_and_store(file):
    """
    Processes the given file: splits it into chunks, generates embeddings, 
    and upserts the data into the Pinecone index.
    """
    data = load_document(file)
    if not data.strip():
        print("File content is empty or invalid.")
        return

    # Wrap data in a Document object
    document = Document(page_content=data, metadata={"file_name": file})

    # Split text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=20, chunk_overlap=5)
    chunks = splitter.split_documents([document])

    print(f"Processing file: {file}")
    print(f"Number of chunks created: {len(chunks)}")

    if len(chunks) == 0:
        print("No chunks were created. Ensure the file has sufficient content.")
        return

    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)

    # Upsert embeddings with metadata
    for i, chunk in enumerate(chunks):
        chunk_id = f"{file}_chunk_{i}"
        vector = embeddings.embed_query(chunk.page_content)  # Use embed_text for single text
        metadata = chunk.metadata

        # Upsert into Pinecone
        index.upsert(vectors=[
            (chunk_id, vector, metadata)
        ])
        print(f"Upserted chunk {i + 1}/{len(chunks)}")

# Main method to test out
if __name__ == "__main__":
    file_path = "C:\\Users\\nabil\\Downloads\\GithubGPT\\semantic_search\\test.txt"
    print("File size:", os.path.getsize(file_path))
    process_and_store(file_path)
