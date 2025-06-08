import os
import logging
from typing import Dict, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.schema import Document
from chroma_embeding import RecipeDocumentManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecipeChatbot:
    def __init__(self, google_api_key: str):
        """Initialize the recipe chatbot with Google API key."""
        self.google_api_key = google_api_key
        self.llm = None
        self.memory = None
        self.vector_db = None
        self.conversation_chain = None
        self.document_manager = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all chatbot components."""
        try:
            # Initialize Google Generative AI Chat model with better settings for recipes
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                temperature=0.7,
                max_output_tokens=2048,
                google_api_key=self.google_api_key
            )
            
            # Initialize memory for conversation context
            self.memory = ConversationBufferWindowMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key='answer',
                k=8  # Keep last 8 exchanges for recipe context
            )
            
            # Initialize document manager
            self.document_manager = RecipeDocumentManager()
            
            # Create embeddings model
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=self.google_api_key
            )
            
            # Initialize Chroma DB with LangChain wrapper
            self.vector_db = Chroma(
                client=self.document_manager.client,
                collection_name="recipes",
                embedding_function=embeddings
            )
            
            # Create enhanced retriever for recipe search
            self.retriever = ContextualCompressionRetriever(
                base_compressor=LLMChainExtractor.from_llm(self.llm),
                base_retriever=self.vector_db.as_retriever(
                    search_kwargs={
                        "k": 6  # Number of documents to retrieve
                    }
                )
            )
            
            # Enhanced prompt template for recipe assistance
            self.prompt_template = PromptTemplate(
                input_variables=["chat_history", "question", "context"],
                template="""You are a helpful recipe assistant. Use the following context to answer the question.
                If you don't know the answer, just say that you don't know. Don't try to make up an answer.
                
                When describing recipes, follow these guidelines:
                1. Write a concise description (150-200 words) that includes:
                   - Main ingredients and their key characteristics
                   - Cooking method and technique highlights
                   - Flavor profile and texture
                   - Serving suggestions
                   - Any unique or special features
                2. Avoid repetition and generic phrases
                3. Focus on what makes the recipe special
                4. Use descriptive but concise language
                
                Context: {context}
                
                Chat History:
                {chat_history}
                
                Question: {question}
                
                Answer:"""
            )
            
            # Create the enhanced ConversationalRetrievalChain
            self.conversation_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=self.retriever,
                memory=self.memory,
                combine_docs_chain_kwargs={"prompt": self.prompt_template}
            )
            
            logger.info("Enhanced recipe chatbot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize chatbot: {str(e)}")
            raise
    
    def get_response(self, user_input: str) -> Dict[str, any]:
        """
        Get a response from the chatbot with enhanced recipe context.
        
        Args:
            user_input (str): The user's question or input
            
        Returns:
            Dict containing answer, sources, recipe metadata, and suggested actions
        """
        if not user_input.strip():
            return {
                "answer": "Hello! I'm your recipe assistant. Ask me about recipes, cooking tips, or tell me what ingredients you have and I'll suggest some delicious dishes you can make!",
                "sources": [],
                "recipes": [],
                "suggestions": ["What ingredients do you have?", "Show me quick dinner recipes", "I need a vegetarian meal"],
                "error": None
            }
        
        try:
            # Enhanced query processing
            processed_query = self._enhance_user_query(user_input)
            
            # Get the response from the conversation chain
            result = self.conversation_chain.invoke({"question": processed_query})
            
            # Extract the answer and source documents
            answer = result["answer"]
            source_docs = result.get("source_documents", [])
            
            # Process and extract recipe information
            recipes_info = self._extract_recipe_info(source_docs)
            unique_sources = self._process_sources(source_docs)
            suggestions = self._generate_follow_up_suggestions(user_input, recipes_info)
            
            # Enhanced response formatting
            formatted_answer = self._format_response(answer, recipes_info)
            
            return {
                "answer": formatted_answer,
                "sources": unique_sources,
                "recipes": recipes_info,
                "suggestions": suggestions,
                "error": None
            }
            
        except Exception as e:
            error_msg = f"I'm sorry, I encountered an issue while searching for recipes. Please try rephrasing your question or ask about a specific dish or ingredient."
            logger.error(f"Error in get_response: {str(e)}")
            
            return {
                "answer": error_msg,
                "sources": [],
                "recipes": [],
                "suggestions": ["Try asking about a specific ingredient", "Search for a cuisine type", "Ask for cooking tips"],
                "error": str(e)
            }
    
    def _enhance_user_query(self, user_input: str) -> str:
        """Enhance user query for better recipe retrieval."""
        query = user_input.lower()
        
        # Add context keywords for better matching
        enhancements = []
        
        # Detect ingredient-based queries
        if any(word in query for word in ['have', 'using', 'with', 'got']):
            enhancements.append("recipe ingredients")
        
        # Detect time-based queries
        if any(word in query for word in ['quick', 'fast', 'easy', '30 min', 'hour']):
            enhancements.append("cooking time")
        
        # Detect dietary preferences
        if any(word in query for word in ['vegetarian', 'vegan', 'gluten-free', 'low-fat']):
            enhancements.append("dietary")
        
        # Detect cuisine types
        cuisines = ['italian', 'mexican', 'asian', 'indian', 'american', 'chinese', 'thai']
        if any(cuisine in query for cuisine in cuisines):
            enhancements.append("cuisine")
        
        # Return enhanced query
        if enhancements:
            return f"{user_input} {' '.join(enhancements)}"
        return user_input
    
    def _extract_recipe_info(self, source_docs: List[Document]) -> List[Dict]:
        """Extract structured recipe information from source documents."""
        recipes = []
        seen_recipes = set()
        
        for doc in source_docs[:6]:  # Limit to top 6 recipes
            try:
                metadata = doc.metadata
                recipe_name = metadata.get('recipe_name', metadata.get('title', 'Unknown Recipe'))
                
                # Avoid duplicates
                if recipe_name in seen_recipes:
                    continue
                seen_recipes.add(recipe_name)
                
                # Extract recipe details from content and metadata
                recipe_info = {
                    "name": recipe_name,
                    "rating": metadata.get('rating', 'Not rated'),
                    "prep_time": metadata.get('prep_time_minutes'),
                    "cook_time": metadata.get('cook_time_minutes'),
                    "total_time": metadata.get('total_time_minutes'),
                    "servings": metadata.get('servings'),
                    "difficulty": metadata.get('difficulty_level', 'Unknown'),
                    "cuisine": metadata.get('cuisine_type', 'International'),
                    "category": metadata.get('main_category', 'General'),
                    "main_ingredients": metadata.get('main_ingredients', []),
                    "cooking_methods": metadata.get('cooking_methods', []),
                    "dietary_info": metadata.get('dietary_info', []),
                    "has_image": metadata.get('has_image', False),
                    "source_url": metadata.get('source_url'),
                    "instructions": doc.page_content,  # Store full instructions for description generation
                    "image_url": metadata.get('image_url', '')  # Get image URL from metadata
                }
                
                recipes.append(recipe_info)
                
            except Exception as e:
                logger.warning(f"Error extracting recipe info: {e}")
                continue
        
        return recipes
    
    def _process_sources(self, source_docs: List[Document]) -> List[Dict]:
        """Process source documents to avoid duplicates."""
        unique_sources = []
        seen_sources = set()
        
        for doc in source_docs:
            source = doc.metadata.get('source', 'Recipe Database')
            recipe_name = doc.metadata.get('recipe_name', 'Unknown Recipe')
            
            source_key = f"{source}_{recipe_name}"
            if source_key not in seen_sources:
                seen_sources.add(source_key)
                unique_sources.append({
                    "source": source,
                    "recipe_name": recipe_name,
                    "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                })
        
        return unique_sources[:5]  # Limit to 5 sources
    
    def _generate_follow_up_suggestions(self, user_input: str, recipes: List[Dict]) -> List[str]:
        """Generate contextual follow-up suggestions."""
        suggestions = []
        query = user_input.lower()
        
        # Based on query type
        if 'ingredient' in query or 'have' in query:
            suggestions.extend([
                "Show me the full recipe for the first suggestion",
                "What can I substitute if I'm missing an ingredient?",
                "How long will this take to prepare?"
            ])
        elif any(time_word in query for time_word in ['quick', 'fast', 'easy']):
            suggestions.extend([
                "Show me recipes under 30 minutes",
                "What are some meal prep options?",
                "Give me beginner-friendly recipes"
            ])
        elif len(recipes) > 1:
            suggestions.extend([
                f"Tell me more about {recipes[0]['name']}",
                "Compare the difficulty of these recipes",
                "Which recipe has the highest rating?"
            ])
        
        # Generic helpful suggestions
        if len(suggestions) < 3:
            suggestions.extend([
                "Show me ingredients and instructions",
                "What cuisine type would you recommend?",
                "Give me cooking tips for beginners"
            ])
        
        return suggestions[:3]
    
    def _format_response(self, answer: str, recipes: List[Dict]) -> str:
        """Format the response with enhanced recipe information."""
        if not recipes:
            return answer
        
        # Add recipe summary if multiple recipes found
        if len(recipes) > 1:
            answer += f"\n\n📚 **Found {len(recipes)} recipes for you:**\n"
            for i, recipe in enumerate(recipes[:3], 1):
                time_info = ""
                if recipe.get('total_time'):
                    time_info = f" • ⏱️ {recipe['total_time']} min"
                elif recipe.get('cook_time'):
                    time_info = f" • ⏱️ {recipe['cook_time']} min"
                
                rating_info = ""
                if recipe.get('rating') and recipe['rating'] != 'Not rated':
                    rating_info = f" • ⭐ {recipe['rating']}/5"
                
                # Get a concise description from the recipe content
                description = self._generate_recipe_description(recipe)
                
                # Add image URL to the response
                image_url = recipe.get('image_url', '')
                image_html = f'<img src="{image_url}" alt="{recipe["name"]}" style="max-width: 300px; border-radius: 8px; margin: 10px 0;">' if image_url else ''
                
                answer += f"{i}. **{recipe['name']}** ({recipe.get('difficulty', 'Medium')}){time_info}{rating_info}\n"
                if image_url:
                    answer += f"   {image_html}\n"
                answer += f"   {description}\n\n"
        
        return answer
    
    def _generate_recipe_description(self, recipe: Dict) -> str:
        """Generate a concise, descriptive summary of the recipe."""
        try:
            # Create a prompt for Gemini to generate a description
            description_prompt = f"""Write a concise, engaging description (150-200 words) for this recipe:
            Name: {recipe['name']}
            Ingredients: {recipe.get('main_ingredients', [])}
            Instructions: {recipe.get('instructions', '')}
            Cooking Method: {recipe.get('cooking_methods', [])}
            Cuisine: {recipe.get('cuisine', '')}
            Category: {recipe.get('category', '')}
            
            Focus on:
            1. Key ingredients and their roles
            2. Cooking technique highlights
            3. Flavor profile and texture
            4. Serving suggestions
            5. What makes this recipe special
            
            Keep it concise and avoid repetition."""
            
            # Get description from Gemini
            response = self.llm.invoke(description_prompt)
            description = response.content.strip()
            
            # Ensure the description is not too long
            if len(description) > 200:
                description = ' '.join(description.split()[:200]) + '...'
            
            return description
            
        except Exception as e:
            logger.error(f"Error generating recipe description: {e}")
            # Fallback to a basic description
            return f"A {recipe.get('cuisine', 'delicious')} {recipe.get('category', 'dish')} that's {recipe.get('difficulty', 'moderately')} difficult to prepare."
    
    def search_recipes(self, query="", filters=None, cooking_time=30):
        """Search for recipes with filters."""
        try:
            # Get base results from ChromaDB
            results = self.document_manager.search_recipes(query, n_results=20)
            
            if not results or not results['documents']:
                return []
            
            # Process and filter results
            filtered_recipes = []
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                # Extract recipe information
                recipe_info = self._parse_recipe_document(doc)
                
                # Apply filters
                if self._apply_filters(recipe_info, filters, cooking_time):
                    filtered_recipes.append({
                        'name': metadata['name'],
                        'image': metadata.get('image_url', ''),  # Get image_url from metadata
                        'rating': metadata['rating'],
                        'type': 'Vegetarian' if 'veg' in filters else 'Non-Vegetarian',
                        'servings': recipe_info.get('servings', 'N/A'),
                        'description': recipe_info.get('description', '')
                    })
            
            return filtered_recipes[:10]  # Return top 10 results
            
        except Exception as e:
            logger.error(f"Error in search_recipes: {e}")
            return []

    def _parse_recipe_document(self, doc):
        """Parse recipe document into structured format."""
        try:
            # Split document into sections
            sections = doc.split('\n\n')
            recipe_info = {}
            
            for section in sections:
                if section.startswith('Ingredients:'):
                    recipe_info['ingredients'] = section.replace('Ingredients:', '').strip()
                elif section.startswith('Instructions:'):
                    recipe_info['instructions'] = section.replace('Instructions:', '').strip()
                elif section.startswith('Nutrition Information:'):
                    recipe_info['nutrition'] = section.replace('Nutrition Information:', '').strip()
            
            # Extract servings from instructions or ingredients
            if 'instructions' in recipe_info:
                # Look for serving information in instructions
                if 'serves' in recipe_info['instructions'].lower():
                    recipe_info['servings'] = recipe_info['instructions'].split('serves')[1].split()[0]
            
            # Create a short description
            if 'instructions' in recipe_info:
                recipe_info['description'] = ' '.join(recipe_info['instructions'].split()[:20]) + '...'
            
            return recipe_info
            
        except Exception as e:
            logger.error(f"Error parsing recipe document: {e}")
            return {}

    def _apply_filters(self, recipe_info, filters, cooking_time):
        """Apply filters to recipe information."""
        if not filters:
            return True
            
        try:
            # Check dietary preference
            if 'veg' in filters and 'non-veg' in recipe_info.get('type', '').lower():
                return False
            if 'non-veg' in filters and 'veg' in recipe_info.get('type', '').lower():
                return False
            
            # Check meal time
            if any(time in filters for time in ['breakfast', 'lunch', 'dinner']):
                if not any(time in recipe_info.get('type', '').lower() for time in ['breakfast', 'lunch', 'dinner']):
                    return False
            
            # Check meal type
            if any(type in filters for type in ['dessert', 'snacks', 'main']):
                if not any(type in recipe_info.get('type', '').lower() for type in ['dessert', 'snacks', 'main']):
                    return False
            
            # Check cooking time
            if 'cooking_time' in recipe_info:
                if int(recipe_info['cooking_time']) > cooking_time:
                    return False
            
            # Check servings
            if any(serving in filters for serving in ['servings-1-2', 'servings-3-4', 'servings-5+']):
                servings = int(recipe_info.get('servings', '0').split()[0])
                if 'servings-1-2' in filters and servings > 2:
                    return False
                if 'servings-3-4' in filters and (servings < 3 or servings > 4):
                    return False
                if 'servings-5+' in filters and servings < 5:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return True
    
    def clear_memory(self):
        """Clear the conversation memory."""
        try:
            self.memory.clear()
            logger.info("Memory cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing memory: {e}")
            return False
    
    def get_memory_summary(self) -> List[str]:
        """Get a summary of the current conversation memory."""
        try:
            messages = self.memory.chat_memory.messages
            return [msg.content for msg in messages[-10:]]  # Last 10 messages
        except Exception as e:
            logger.error(f"Error getting memory summary: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, any]:
        """Get statistics about the recipe collection."""
        try:
            return self.document_manager.get_collection_stats()
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

# Global chatbot instance for Flask integration
_chatbot_instance = None

def get_chatbot_instance():
    """Get or create the global chatbot instance."""
    global _chatbot_instance
    if _chatbot_instance is None:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is not set")
        _chatbot_instance = RecipeChatbot(google_api_key)
    return _chatbot_instance

def chatbot_response(user_input: str) -> Dict[str, any]:
    """
    Flask-compatible function to get enhanced chatbot response.
    
    Args:
        user_input (str): The user's question or input
        
    Returns:
        Dict: Complete response with recipes, suggestions, and metadata
    """
    try:
        chatbot = get_chatbot_instance()
        return chatbot.get_response(user_input)
    except Exception as e:
        logger.error(f"Error in chatbot_response: {str(e)}")
        return {
            "answer": f"I apologize, but I encountered an error. Please try rephrasing your question.",
            "sources": [],
            "recipes": [],
            "suggestions": ["Try a different recipe search", "Ask about cooking tips", "Search by ingredient"],
            "error": str(e)
        }

def search_recipes_with_filters(**filters) -> List[Dict]:
    """Search recipes using specific filters."""
    try:
        chatbot = get_chatbot_instance()
        return chatbot.search_recipes(**filters)
    except Exception as e:
        logger.error(f"Error in filtered search: {e}")
        return []

def main():
    """Main function to run the enhanced chatbot."""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    if not google_api_key:
        print("Error: GOOGLE_API_KEY environment variable is not set")
        return
    
    try:
        print("🍳 Initializing Enhanced Recipe Chatbot...")
        chatbot = RecipeChatbot(google_api_key)
        
        # Show collection stats
        stats = chatbot.get_collection_stats()
        print(f"📊 Recipe Database: {stats.get('total_recipes', 0)} recipes loaded")
        if stats.get('categories'):
            print(f"📁 Categories: {', '.join(stats['categories'][:5])}")
        
        print("\n🤖 Recipe Assistant ready! I can help you with:")
        print("  • Recipe suggestions based on ingredients you have")
        print("  • Cooking tips and techniques")
        print("  • Dietary restriction accommodations")
        print("  • Time-based meal planning")
        print("\nType 'quit' to exit, 'clear' to reset conversation, or 'stats' for database info.\n")
        
        while True:
            user_input = input("🧑‍🍳 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Happy cooking! Come back anytime for more recipe ideas!")
                break
            elif user_input.lower() == 'clear':
                chatbot.clear_memory()
                print("🧹 Conversation cleared! What would you like to cook today?")
                continue
            elif user_input.lower() == 'stats':
                stats = chatbot.get_collection_stats()
                print(f"\n📊 Database Stats:")
                for key, value in stats.items():
                    if key != 'error':
                        print(f"  {key}: {value}")
                print()
                continue
            elif not user_input:
                continue
            
            # Get enhanced response
            response = chatbot.get_response(user_input)
            
            print(f"\n🤖 Assistant: {response['answer']}")
            
            # Show follow-up suggestions
            if response.get('suggestions'):
                print(f"\n💡 Try asking:")
                for i, suggestion in enumerate(response['suggestions'], 1):
                    print(f"  {i}. {suggestion}")
            
            print()  # Add spacing
    
    except KeyboardInterrupt:
        print("\n\n👋 Happy cooking!")
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")

# Export functions for Flask integration
__all__ = ['chatbot_response', 'search_recipes_with_filters', 'RecipeChatbot', 'get_chatbot_instance']

if __name__ == "__main__":
    main()