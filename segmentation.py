# segmentation.py# In a new script, e.g., 'segmentation.py'
import os
import argparse
import json
import google.generativeai as genai
import dotenv

# Load environment variables from a .env file
dotenv.load_dotenv()
# Suppress noisy logs from some backends used by SDKs
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")

# --- Configuration ---
# IMPORTANT: It's better to use environment variables in production
# For this example, you can paste your key here directly.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def read_reconstructed_text(file_path: str) -> str:
    """Reads the content of the OCR'd text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return ""
    

def segment_contract_with_gemini(contract_text: str) -> list:
    """
    Uses the Gemini API to segment a contract text into clauses.

    Args:
        contract_text: The full text of the contract.

    Returns:
        A list of dictionaries, where each dictionary represents a clause.
    """
    # Initialize the Gemini model
    model = genai.GenerativeModel('gemini-1.5-flash')

    # This prompt is engineered to force the model to return a structured JSON.
    prompt = f"""
    You are a specialized legal document parser with expertise in contract structure, clause identification, and grammar correction (grammar only, no altering legal meaning).  

Your task: Perform **clause segmentation** on the given contract text.  
A “clause” is a logically distinct section of a contract, often beginning with a title, number, or specific keyword (e.g., "1. Definitions", "Article II: Confidentiality", "Termination", etc.), and ending where the next clause begins.  

Instructions:
1. **Detect and separate clauses** even if they are not explicitly numbered or titled.  
2. If a clause has no title, **infer a concise, descriptive title** based on its content (e.g., "Governing Law", "Payment Terms").  
3. **Preserve full clause content** but correct grammar and minor formatting issues without altering legal meaning.  
4. Each clause should be a self-contained text block — do not merge multiple clauses.  
5. Maintain the original order of clauses.  

Output format:
Return as a **valid JSON array** where each object has:
- `"clause_title"`: A concise title or identifier.
- `"clause_text"`: The full, corrected text of that clause.

Example Output:
[
    "clause_title": "1. Definitions",
    "clause_text": "This Agreement defines the following terms: ..."
    
    "clause_title": "2. Confidentiality",
    "clause_text": "The parties agree to maintain confidentiality ..."
]

### Contract Text:
---
{contract_text}
---
"""

    try:
        response = model.generate_content(prompt)
        
        # The model's output might be enclosed in markdown for JSON, so we clean it.
        cleaned_json_string = response.text.strip().replace("```json", "").replace("```", "")
        
        # Parse the JSON string into a Python list
        clauses = json.loads(cleaned_json_string)
        return clauses

    except Exception as e:
        print(f"An error occurred while calling the Gemini API or parsing its response: {e}")
        print(f"Raw response text was: {response.text}")
        return []

# Example Usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Contract clause segmentation")
    parser.add_argument(
        "--input",
        dest="input_file",
        type=str,
        default="Documents/sample_contract.txt",
        help="Path to input text file (from OCR)",
    )
    parser.add_argument(
        "--output",
        dest="output_file",
        type=str,
        default="documents/segmented_clauses.json",
        help="Path to output JSON for segmented clauses",
    )
    args = parser.parse_args()

    input_file_path = args.input_file
    output_file_path = args.output_file

    print(f"1. Reading text from '{input_file_path}'...")
    contract_content = read_reconstructed_text(input_file_path)

    if contract_content:
        print("2. Sending text to Gemini for clause segmentation...")
        segmented_clauses = segment_contract_with_gemini(contract_content)

        if segmented_clauses:
            print(f"\nSuccessfully segmented the document into {len(segmented_clauses)} clauses.")
            
            # --- Displaying the result ---
            print("\n--- First 2 Clauses ---")
            for clause in segmented_clauses[:2]:
                print(f"\nTitle: {clause['clause_title']}")
                print(f"Text: {clause['clause_text'][:150]}...") # Preview first 150 chars

            # --- Saving the result ---
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(segmented_clauses, f, indent=4)
            
            print(f"\nStructured clauses saved to '{output_file_path}'")