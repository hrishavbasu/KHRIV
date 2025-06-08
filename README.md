# Recipe Search and Chatbot

An intelligent recipe search and chatbot application that uses Google's Gemini AI for semantic search and natural language processing. The application provides a modern web interface for searching recipes with various filters and viewing recipe details with images.

## Features

- 🔍 **Intelligent Recipe Search**

  - Semantic search using Gemini embeddings
  - Filter recipes by:
    - Dietary preferences (veg/non-veg)
    - Meal time (breakfast, lunch, dinner)
    - Cooking time (15-60 minutes)
    - Serving size
    - Meal type (dessert, snacks, etc.)
  - Recipe cards with:
    - Recipe name
    - High-quality images
    - Rating
    - Type (veg/non-veg)
    - Serving size
    - Concise description

- 💬 **Smart Chat Interface**

  - Natural language recipe queries
  - Contextual follow-up suggestions
  - Detailed recipe information
  - Cooking tips and techniques

- 🗄️ **Vector Database**
  - ChromaDB for efficient recipe storage and retrieval
  - Gemini embeddings for semantic search
  - Persistent storage of recipe data

## Setup

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd recipe-search-chatbot
   ```

2. **Create and activate virtual environment**

   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   export GOOGLE_API_KEY="your-google-api-key"  # Required for Gemini AI
   ```

5. **Initialize the database**

   ```bash
   python chroma_embeding.py
   ```

6. **Run the application**

   ```bash
   python app.py
   ```

7. **Access the web interface**
   - Open your browser and go to `http://localhost:8080`

## Project Structure

- `app.py` - Flask web application and API endpoints
- `chatbot.py` - Recipe chatbot implementation with Gemini AI
- `chroma_embeding.py` - ChromaDB setup and recipe embedding
- `recipes.csv` - Recipe dataset
- `requirements.txt` - Python dependencies

## API Endpoints

- `POST /chat` - Main chat interface
- `POST /search` - Advanced recipe search with filters
- `POST /suggest` - Ingredient-based suggestions
- `GET /stats` - Database statistics

## Dependencies

- Flask - Web framework
- LangChain - AI/ML framework
- ChromaDB - Vector database
- Google Generative AI - Embeddings and chat
- Flask-CORS - Cross-origin resource sharing

## Notes

- The application uses port 8080 by default to avoid conflicts with AirPlay on macOS
- Recipe images are stored in the CSV file and served through the web interface
- The chatbot maintains conversation context for better recipe suggestions
- All recipe data is stored in ChromaDB for efficient retrieval

## Contributing

Feel free to submit issues and enhancement requests!
