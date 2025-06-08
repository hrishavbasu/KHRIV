from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import logging
from chatbot import chatbot_response, search_recipes_with_filters, get_chatbot_instance, RecipeChatbot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Initialize the chatbot with Google API key
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set!")
chatbot = RecipeChatbot(google_api_key=google_api_key)

# Simple HTML template for testing
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recipe Search</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        .search-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .search-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .search-input {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        
        .search-button {
            padding: 12px 24px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        
        .filters {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .filter-group {
            background: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
        }
        
        .filter-group h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #666;
        }
        
        .filter-options {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .filter-button {
            padding: 6px 12px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 15px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .filter-button.active {
            background: #4CAF50;
            color: white;
            border-color: #4CAF50;
        }
        
        .recipe-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .recipe-card {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        
        .recipe-card:hover {
            transform: translateY(-5px);
        }
        
        .recipe-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        
        .recipe-content {
            padding: 15px;
        }
        
        .recipe-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }
        
        .recipe-title {
            margin: 0;
            font-size: 18px;
            color: #333;
        }
        
        .recipe-rating {
            display: flex;
            align-items: center;
            gap: 5px;
            color: #ff9800;
        }
        
        .recipe-tags {
            display: flex;
            gap: 8px;
            margin-bottom: 10px;
        }
        
        .recipe-tag {
            padding: 4px 8px;
            background: #f0f0f0;
            border-radius: 12px;
            font-size: 12px;
            color: #666;
        }
        
        .recipe-description {
            color: #666;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .time-slider {
            width: 100%;
            margin: 10px 0;
        }
        
        .time-labels {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="search-container">
        <div class="search-bar">
            <input type="text" id="search-input" class="search-input" placeholder="Search for recipes...">
            <button onclick="searchRecipes()" class="search-button">Search</button>
        </div>
        
        <div class="filters">
            <div class="filter-group">
                <h3>Dietary Preference</h3>
                <div class="filter-options">
                    <button class="filter-button" onclick="toggleFilter(this, 'veg')">Vegetarian</button>
                    <button class="filter-button" onclick="toggleFilter(this, 'non-veg')">Non-Vegetarian</button>
                </div>
            </div>
            
            <div class="filter-group">
                <h3>Meal Time</h3>
                <div class="filter-options">
                    <button class="filter-button" onclick="toggleFilter(this, 'breakfast')">Breakfast</button>
                    <button class="filter-button" onclick="toggleFilter(this, 'lunch')">Lunch</button>
                    <button class="filter-button" onclick="toggleFilter(this, 'dinner')">Dinner</button>
                </div>
            </div>
            
            <div class="filter-group">
                <h3>Meal Type</h3>
                <div class="filter-options">
                    <button class="filter-button" onclick="toggleFilter(this, 'dessert')">Dessert</button>
                    <button class="filter-button" onclick="toggleFilter(this, 'snacks')">Snacks</button>
                    <button class="filter-button" onclick="toggleFilter(this, 'main')">Main Course</button>
                </div>
            </div>
            
            <div class="filter-group">
                <h3>Cooking Time</h3>
                <input type="range" min="15" max="60" value="30" class="time-slider" id="time-slider">
                <div class="time-labels">
                    <span>15 min</span>
                    <span>60 min</span>
                </div>
            </div>
            
            <div class="filter-group">
                <h3>Servings</h3>
                <div class="filter-options">
                    <button class="filter-button" onclick="toggleFilter(this, 'servings-1-2')">1-2</button>
                    <button class="filter-button" onclick="toggleFilter(this, 'servings-3-4')">3-4</button>
                    <button class="filter-button" onclick="toggleFilter(this, 'servings-5+')">5+</button>
                </div>
            </div>
        </div>
    </div>
    
    <div id="recipe-grid" class="recipe-grid">
        <!-- Recipe cards will be dynamically added here -->
    </div>

    <script>
        let activeFilters = new Set();
        
        function toggleFilter(button, filter) {
            button.classList.toggle('active');
            if (button.classList.contains('active')) {
                activeFilters.add(filter);
            } else {
                activeFilters.delete(filter);
            }
        }
        
        function createRecipeCard(recipe) {
            return `
                <div class="recipe-card">
                    <img src="${recipe.image}" alt="${recipe.name}" class="recipe-image">
                    <div class="recipe-content">
                        <div class="recipe-header">
                            <h3 class="recipe-title">${recipe.name}</h3>
                            <div class="recipe-rating">
                                ⭐ ${recipe.rating}
                            </div>
                        </div>
                        <div class="recipe-tags">
                            <span class="recipe-tag">${recipe.type}</span>
                            <span class="recipe-tag">${recipe.servings} servings</span>
                        </div>
                        <p class="recipe-description">${recipe.description}</p>
                    </div>
                </div>
            `;
        }
        
        async function searchRecipes() {
            const searchQuery = document.getElementById('search-input').value;
            const cookingTime = document.getElementById('time-slider').value;
            
            try {
                const response = await fetch('/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: searchQuery,
                        filters: Array.from(activeFilters),
                        cooking_time: parseInt(cookingTime)
                    })
                });
                
                const data = await response.json();
                const recipeGrid = document.getElementById('recipe-grid');
                recipeGrid.innerHTML = '';
                
                data.recipes.forEach(recipe => {
                    recipeGrid.innerHTML += createRecipeCard(recipe);
                });
            } catch (error) {
                console.error('Error searching recipes:', error);
            }
        }
        
        // Initial search on page load
        searchRecipes();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    """Serve a simple chat interface for testing."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    """Enhanced chat endpoint with full response data."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "No message provided"}), 400
        
        user_input = data['message'].strip()
        if not user_input:
            return jsonify({"error": "Empty message"}), 400
        
        # Get enhanced response from chatbot
        response = chatbot_response(user_input)
        
        # Return complete response data
        return jsonify({
            "answer": response.get("answer", "I'm sorry, I couldn't process that request."),
            "recipes": response.get("recipes", []),
            "sources": response.get("sources", []),
            "suggestions": response.get("suggestions", []),
            "error": response.get("error")
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({
            "error": "Internal server error",
            "answer": "I'm sorry, I encountered an error while processing your request. Please try again."
        }), 500

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        filters = data.get('filters', [])
        cooking_time = data.get('cooking_time', 30)
        
        # Get search results from the chatbot
        results = chatbot.search_recipes(
            query=query,
            filters=filters,
            cooking_time=cooking_time
        )
        
        return jsonify({
            'recipes': results
        })
    except Exception as e:
        logger.error(f"Error in search endpoint: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/suggest', methods=['POST'])
def suggest_by_ingredients():
    """Get recipe suggestions based on available ingredients."""
    try:
        data = request.get_json()
        ingredients = data.get('ingredients', [])
        
        if not ingredients:
            return jsonify({"error": "No ingredients provided"}), 400
        
        # Create ingredient-based query
        ingredient_query = f"recipes with {', '.join(ingredients)}"
        response = chatbot_response(ingredient_query)
        
        return jsonify({
            "suggestions": response.get("recipes", []),
            "answer": response.get("answer", ""),
            "count": len(response.get("recipes", []))
        })
        
    except Exception as e:
        logger.error(f"Error in suggest endpoint: {e}")
        return jsonify({"error": "Suggestion failed", "suggestions": []}), 500

@app.route('/clear', methods=['POST'])
def clear_conversation():
    """Clear the conversation memory."""
    try:
        chatbot.clear_memory()
        return jsonify({"status": "Memory cleared successfully"})
    except Exception as e:
        logger.error(f"Error clearing memory: {e}")
        return jsonify({"error": "Failed to clear memory"}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    try:
        stats = chatbot.get_collection_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test basic chatbot functionality
        stats = chatbot.get_collection_stats()
        
        return jsonify({
            "status": "healthy",
            "database_status": "connected",
            "recipe_count": stats.get("total_recipes", 0),
            "timestamp": "2024-01-01"  # You can use datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/filters', methods=['GET'])
def get_available_filters():
    """Get available filter options for the frontend."""
    try:
        stats = chatbot.get_collection_stats()
        
        return jsonify({
            "cuisine_types": list(stats.get("cuisine_types", {}).keys()),
            "categories": list(stats.get("categories", {}).keys()),
            "difficulty_levels": ["Easy", "Medium", "Hard"],
            "dietary_options": [
                "vegetarian-friendly",
                "dairy-free-option", 
                "gluten-free-option",
                "low-fat",
                "low-sodium",
                "high-fiber"
            ],
            "time_ranges": [
                {"label": "Quick (under 30 min)", "value": 30},
                {"label": "Medium (30-60 min)", "value": 60},
                {"label": "Long (1-2 hours)", "value": 120},
                {"label": "Extended (2+ hours)", "value": 240}
            ]
        })
    except Exception as e:
        logger.error(f"Error getting filters: {e}")
        return jsonify({"error": "Failed to get filter options"}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500

# Additional utility routes for development
@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify API is working."""
    return jsonify({
        "message": "Recipe Chatbot API is working!",
        "endpoints": [
            "POST /chat - Main chat interface",
            "POST /search - Advanced recipe search",
            "POST /suggest - Ingredient-based suggestions", 
            "POST /clear - Clear conversation memory",
            "GET /stats - Database statistics",
            "GET /health - Health check",
            "GET /filters - Available filter options",
            "GET /test - This test endpoint"
        ]
    })

if __name__ == '__main__':
    # Get port from environment or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    logger.info("🍳 Starting Recipe Chatbot API...")
    logger.info(f"🌐 Access the web interface at: http://localhost:{port}")
    logger.info("📡 API endpoints available:")
    logger.info("  POST /chat - Main chat interface")
    logger.info("  POST /search - Advanced recipe search")
    logger.info("  POST /suggest - Ingredient-based suggestions")
    logger.info("  GET /stats - Database statistics")
    
    app.run(debug=True, host='0.0.0.0', port=port)