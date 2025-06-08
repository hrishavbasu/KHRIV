# Add this to a new file called debug_db.py to check your database

import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

# Get the API key
google_api_key = os.getenv("GOOGLE_API_KEY")

if not google_api_key:
    print("Error: GOOGLE_API_KEY environment variable is not set")
    exit(1)

# Create embedding model
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=google_api_key
)

# Initialize Chroma DB
vector_db = Chroma(
    embedding_function=embeddings,
    collection_name="recipe_collection",
    persist_directory="./recipe_chroma_db"
)

# Check if database has any documents
try:
    # Get all documents
    all_docs = vector_db.get()
    print(f"Total documents in database: {len(all_docs['ids'])}")
    
    if len(all_docs['ids']) == 0:
        print("❌ DATABASE IS EMPTY!")
        print("You need to run your document ingestion script first.")
    else:
        print("✅ Database has documents")
        
        # Show first few documents
        print("\nFirst 3 documents:")
        for i in range(min(3, len(all_docs['ids']))):
            print(f"Document {i+1}:")
            print(f"  ID: {all_docs['ids'][i]}")
            print(f"  Content preview: {all_docs['documents'][i][:100]}...")
            if all_docs['metadatas'][i]:
                print(f"  Metadata: {all_docs['metadatas'][i]}")
            print()
    
    # Test search for apple desserts
    print("Testing search for 'apple dessert':")
    results = vector_db.similarity_search("apple dessert", k=5)
    print(f"Found {len(results)} results")
    
    for i, doc in enumerate(results):
        print(f"Result {i+1}:")
        print(f"  Content: {doc.page_content[:150]}...")
        print(f"  Source: {doc.metadata.get('source', 'Unknown')}")
        print()

except Exception as e:
    print(f"Error accessing database: {e}")
    print("Make sure your database path and collection name are correct.")