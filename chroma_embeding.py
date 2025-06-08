import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import pandas as pd
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecipeDocumentManager:
    def __init__(self, persist_directory="./my_chroma_db"):
        self.persist_directory = persist_directory
        
        # Initialize Google Gemini embedding function
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY environment variable is not set!")
            
        self.embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=os.getenv("GOOGLE_API_KEY"),
            model_name="models/embedding-001"  # Using Gemini's embedding model
        )
        
        # Initialize ChromaDB client with the embedding function
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(
                name="recipes",
                embedding_function=self.embedding_function
            )
            logger.info(f"Loaded existing collection 'recipes' from {persist_directory}")
        except Exception as e:
            logger.info(f"Creating new collection 'recipes' in {persist_directory}")
            self.collection = self.client.create_collection(
                name="recipes",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
        
        # Verify collection exists and has data
        try:
            stats = self.get_collection_stats()
            logger.info(f"Collection stats: {stats}")
        except Exception as e:
            logger.error(f"Error verifying collection: {e}")
            raise

    def format_recipe_text(self, recipe_data):
        """Format recipe data into a structured text string."""
        try:
            # Extract recipe components
            name = recipe_data[1] if len(recipe_data) > 1 else "Unknown Recipe"
            ingredients = recipe_data[7] if len(recipe_data) > 7 else ""
            instructions = recipe_data[8] if len(recipe_data) > 8 else ""
            nutrition = recipe_data[12] if len(recipe_data) > 12 else ""
            
            # Create a structured text format
            formatted_text = f"""
Recipe: {name}

Ingredients:
{ingredients}

Instructions:
{instructions}

Nutrition Information:
{nutrition}
"""
            return formatted_text.strip()
        except Exception as e:
            logger.error(f"Error formatting recipe: {e}")
            return str(recipe_data)  # Fallback to string representation

    def add_recipe(self, recipe_data, recipe_id=None):
        """Add a recipe to the collection."""
        try:
            # Format recipe data into text
            recipe_text = self.format_recipe_text(recipe_data)
            
            # Generate a unique ID if not provided
            if recipe_id is None:
                recipe_id = f"recipe_{len(self.collection.get()['ids'])}"
            
            # Add to collection
            self.collection.add(
                documents=[recipe_text],
                ids=[recipe_id],
                metadatas=[{
                    "name": recipe_data[1] if len(recipe_data) > 1 else "Unknown",
                    "rating": recipe_data[9] if len(recipe_data) > 9 else "0",
                    "url": recipe_data[10] if len(recipe_data) > 10 else "",
                    "category": recipe_data[11] if len(recipe_data) > 11 else "",
                    "image_url": recipe_data[14] if len(recipe_data) > 14 else ""  # Add image URL from 14th index
                }]
            )
            logger.info(f"Added recipe: {recipe_data[0]}")
            return True
        except Exception as e:
            logger.error(f"Error adding recipe: {e}")
            return False

    def search_recipes(self, query, n_results=5):
        """Search for recipes using semantic similarity."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'distances', 'metadatas']
            )
            return results
        except Exception as e:
            logger.error(f"Error searching recipes: {e}")
            return None

    def get_collection_stats(self):
        """Get statistics about the collection."""
        try:
            collection_data = self.collection.get()
            return {
                "total_recipes": len(collection_data['ids']),
                "metadata_fields": list(collection_data['metadatas'][0].keys()) if collection_data['metadatas'] else []
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    def delete_collection(self):
        """Delete the existing collection."""
        try:
            self.client.delete_collection(name="recipes")
            logger.info("Successfully deleted existing collection")
            return True
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            return False

def main():
    # Initialize the document manager
    manager = RecipeDocumentManager()
    
    # Delete existing collection
    logger.info("Deleting existing collection...")
    manager.delete_collection()
    
    # Recreate the collection
    manager = RecipeDocumentManager()
    
    # Read the CSV file
    try:
        df = pd.read_csv("recipes.csv")
        logger.info(f"Loaded {len(df)} recipes from CSV")
        
        # Add each recipe to ChromaDB
        for index, row in df.iterrows():
            recipe_data = row.tolist()
            manager.add_recipe(recipe_data, f"recipe_{index}")
        
        # Get and display collection statistics
        stats = manager.get_collection_stats()
        logger.info(f"Collection statistics: {stats}")
        
        # Test search functionality
        test_query = "Show me a dessert recipe with apples"
        search_results = manager.search_recipes(test_query, n_results=3)
        if search_results:
            logger.info(f"\nTest search results for '{test_query}':")
            for i, (doc, metadata) in enumerate(zip(search_results['documents'][0], search_results['metadatas'][0])):
                logger.info(f"\nResult {i+1}:")
                logger.info(f"Recipe: {metadata['name']}")
                logger.info(f"Rating: {metadata['rating']}")
                logger.info(f"Category: {metadata['category']}")
                logger.info(f"Preview: {doc[:200]}...")
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")

if __name__ == "__main__":
    main()