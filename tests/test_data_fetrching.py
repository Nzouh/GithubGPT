import openai

# Load OpenAI API key
openai.api_key = "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"


try:
    # Test OpenAI Embedding API
    response = openai.Embedding.create(
        input=["Hello, world!"],
        model="text-embedding-ada-002"
    )
    print("OpenAI connected successfully!")
    print("Embedding response:", response)
except Exception as e:
    print("OpenAI connection failed:", e)
