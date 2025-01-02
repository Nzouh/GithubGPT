import os
from pinecone import Pinecone

# Load environment variables
PINECONE_KEY = os.getenv("PINECONE_KEY", "your_pinecone_key")
PINECONE_INDEX_HOST = os.getenv("PINECONE_INDEX_HOST", "your_pinecone_index_host").rstrip('/').strip()

# Initialize Pinecone
try:
    pc = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(host=PINECONE_INDEX_HOST)

    # Check index stats
    stats = index.describe_index_stats()
    print("Pinecone connected successfully!")
    print("Index stats:", stats)
except Exception as e:
    print("Pinecone connection failed:", e)
