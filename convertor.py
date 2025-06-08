import pandas as pd
import sys
from datetime import datetime
import re

def clean_text(text):
    """Clean and format text content"""
    if pd.isna(text) or text is None:
        return ""
    
    # Convert to string and clean up
    text = str(text)
    # Replace escaped newlines with actual newlines
    text = text.replace('\\n', '\n')
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_ingredients(ingredients_text):
    """Format ingredients into a bulleted list"""
    if not ingredients_text:
        return ""
    
    # Split by comma and clean each ingredient
    ingredients = [ing.strip() for ing in ingredients_text.split(',')]
    formatted = []
    
    for ingredient in ingredients:
        if ingredient:  # Skip empty ingredients
            formatted.append(f"• {ingredient}")
    
    return '\n'.join(formatted)

def format_directions(directions_text):
    """Format directions into numbered steps"""
    if not directions_text:
        return ""
    
    # Split by common separators
    steps = re.split(r'\.(?=\s*[A-Z])|\\n|\n', directions_text)
    formatted = []
    
    step_num = 1
    for step in steps:
        step = step.strip()
        if step and len(step) > 10:  # Filter out very short fragments
            # Remove trailing period if present
            step = step.rstrip('.')
            formatted.append(f"{step_num}. {step}")
            step_num += 1
    
    return '\n'.join(formatted)

def convert_csv_to_text(csv_file_path, output_file_path):
    """
    Convert CSV file to plain text format
    
    Args:
        csv_file_path (str): Path to the input CSV file
        output_file_path (str): Path to the output text file
    """
    
    try:
        print(f"📖 Reading CSV file: {csv_file_path}")
        
        # Read the CSV file
        df = pd.read_csv(csv_file_path)
        
        print(f"✅ Found {len(df)} recipes to convert")
        
        # Start building the output text
        output_lines = []
        output_lines.append("RECIPE COLLECTION")
        output_lines.append("=" * 60)
        output_lines.append(f"Total Recipes: {len(df)}")
        output_lines.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output_lines.append("")
        
        # Process each recipe
        for index, row in df.iterrows():
            recipe_num = index + 1
            
            # Recipe header
            recipe_name = clean_text(row.get('recipe_name', 'Untitled Recipe'))
            output_lines.append(f"RECIPE {recipe_num}: {recipe_name}")
            output_lines.append("-" * 60)
            
            # Recipe metadata
            if pd.notna(row.get('servings')):
                output_lines.append(f"Servings: {row['servings']}")
            
            if pd.notna(row.get('yield')):
                output_lines.append(f"Yield: {clean_text(row['yield'])}")
            
            if pd.notna(row.get('prep_time')):
                output_lines.append(f"Prep Time: {clean_text(row['prep_time'])}")
            
            if pd.notna(row.get('cook_time')):
                output_lines.append(f"Cook Time: {clean_text(row['cook_time'])}")
            
            if pd.notna(row.get('total_time')):
                output_lines.append(f"Total Time: {clean_text(row['total_time'])}")
            
            if pd.notna(row.get('rating')):
                output_lines.append(f"Rating: {row['rating']}/5")
            
            if pd.notna(row.get('cuisine_path')):
                output_lines.append(f"Category: {clean_text(row['cuisine_path'])}")
            
            # Ingredients section
            if pd.notna(row.get('ingredients')):
                output_lines.append("")
                output_lines.append("INGREDIENTS:")
                ingredients = format_ingredients(clean_text(row['ingredients']))
                if ingredients:
                    output_lines.append(ingredients)
            
            # Directions section
            if pd.notna(row.get('directions')):
                output_lines.append("")
                output_lines.append("DIRECTIONS:")
                directions = format_directions(clean_text(row['directions']))
                if directions:
                    output_lines.append(directions)
            
            # Nutrition information
            if pd.notna(row.get('nutrition')):
                output_lines.append("")
                output_lines.append("NUTRITION INFO:")
                output_lines.append(clean_text(row['nutrition']))
            
            # Source URL
            if pd.notna(row.get('url')):
                output_lines.append("")
                output_lines.append(f"Source: {clean_text(row['url'])}")
            
            # Recipe separator
            output_lines.append("")
            output_lines.append("=" * 60)
            output_lines.append("")
            
            # Progress indicator
            if recipe_num % 100 == 0:
                print(f"📝 Processed {recipe_num} recipes...")
        
        # Write to output file
        print(f"💾 Writing to file: {output_file_path}")
        
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        
        # Calculate file size
        import os
        file_size_kb = os.path.getsize(output_file_path) / 1024
        
        print("\n🎉 Conversion completed successfully!")
        print(f"📁 Output file: {output_file_path}")
        print(f"📊 Total recipes: {len(df)}")
        print(f"📄 File size: {file_size_kb:.1f} KB")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find CSV file '{csv_file_path}'")
        return False
    except Exception as e:
        print(f"❌ Error during conversion: {str(e)}")
        return False

def main():
    """Main function to run the converter"""
    
    # Default file paths - modify these as needed
    csv_file = "recipes.csv"
    output_file = "all_recipes.txt"
    
    # Check if custom file paths are provided via command line
    if len(sys.argv) >= 2:
        csv_file = sys.argv[1]
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    
    print("🍽️  Recipe CSV to Plain Text Converter")
    print("=" * 40)
    print(f"Input CSV: {csv_file}")
    print(f"Output TXT: {output_file}")
    print("=" * 40)
    
    # Convert the file
    success = convert_csv_to_text(csv_file, output_file)
    
    if success:
        print(f"\n✨ All {csv_file} recipes have been converted to {output_file}")
        print("You can now open the text file to view all recipes!")
    else:
        print("\n❌ Conversion failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()