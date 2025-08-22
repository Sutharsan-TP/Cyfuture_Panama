import os
import json
from pathlib import Path
from transformers import pipeline, AutoTokenizer
from optimum.onnxruntime import ORTModelForTokenClassification, ORTQuantizer
from optimum.onnxruntime.configuration import QuantizationConfig, QuantizationMode

# Load environment variables from .env (for Hugging Face API token)
import dotenv
dotenv.load_dotenv()
# --- Configuration ---
# --- THE ONLY CHANGE IS ON THIS LINE ---
# Use a public, well-known English NER model
MODEL_ID = "dslim/bert-base-NER"
# Directory to store the standard, exported, and quantized models
ONNX_MODEL_DIR = Path("models/bert_base_ner_onnx")
# The final, quantized model file we want to use (handle naming variations)
QUANTIZED_MODEL_PATH = ONNX_MODEL_DIR / "model_quantized.onnx"
QUANTIZED_MODEL_ALT_PATH = ONNX_MODEL_DIR / "model__quantized.onnx"

# Input and Output files
INPUT_CLAUSES_FILE = "documents/segmented_clauses.json"
OUTPUT_CLAUSES_FILE = "documents/clauses_with_entities.json"

# Post-processing controls
CONFIDENCE_THRESHOLD = 0.85  # filter out low-confidence entities
LABEL_MAP = {
    "ORG": "PARTY",
    "PER": "PERSON",
    "LOC": "LOCATION",
    "MISC": "OTHER",
}


def prepare_quantized_model():
    """
    Checks if a quantized model exists. If not, it downloads, exports,
    and quantizes the model. Then, it loads and returns the quantized model.
    """
    # Treat either filename as valid to avoid re-quantizing unnecessarily
    if not (QUANTIZED_MODEL_PATH.exists() or QUANTIZED_MODEL_ALT_PATH.exists()):
        print(f"Quantized model not found. Starting one-time setup...")
        # 1. Export the base model to ONNX format
        print(f"Step 1/2: Exporting '{MODEL_ID}' to ONNX format...")
        model = ORTModelForTokenClassification.from_pretrained(MODEL_ID, export=True)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        # 2. Apply dynamic INT8 quantization
        print(f"Step 2/2: Quantizing the ONNX model...")
        quantizer = ORTQuantizer.from_pretrained(model)
        dqconfig = QuantizationConfig(
            is_static=False,
            format="QOperator",
            mode=QuantizationMode.IntegerOps,
        )
        quantizer.quantize(
            save_dir=ONNX_MODEL_DIR,
            quantization_config=dqconfig,
            file_suffix="_quantized"
        )
        # Also save the tokenizer to the same directory
        tokenizer.save_pretrained(ONNX_MODEL_DIR)
        print("Model setup complete.")
    else:
        print("Found existing quantized model. Loading it directly.")

    # Load the final quantized model and tokenizer from the directory
    file_name = "model_quantized.onnx"
    if QUANTIZED_MODEL_ALT_PATH.exists() and not QUANTIZED_MODEL_PATH.exists():
        file_name = "model__quantized.onnx"
    quantized_model = ORTModelForTokenClassification.from_pretrained(ONNX_MODEL_DIR, file_name=file_name)
    tokenizer = AutoTokenizer.from_pretrained(ONNX_MODEL_DIR)
    return quantized_model, tokenizer

def load_clauses(file_path: str) -> list:
    """Loads the segmented clauses from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at {file_path}")
        return []


if __name__ == "__main__":
    # 1. Prepare the model (downloads and quantizes only if needed)
    print("--- Preparing NER Model ---")
    ner_model, ner_tokenizer = prepare_quantized_model()

    # 2. Load the segmented clauses
    print("\n--- Loading Data ---")
    clauses = load_clauses(INPUT_CLAUSES_FILE)
    
    if clauses:
        # 3. Create the NER pipeline with the fast, quantized model
        print("\n--- Initializing NER Pipeline ---")
        ner_pipeline = pipeline(
            "token-classification",
            model=ner_model,
            tokenizer=ner_tokenizer,
            aggregation_strategy="simple"
        )

        # 4. Process clauses and extract entities
        print("\n--- Running NER on Clauses ---")
        for i, clause in enumerate(clauses):
            print(f"Processing clause {i+1}/{len(clauses)}: '{clause['clause_title']}'")
            entities = ner_pipeline(clause['clause_text'])
            
            # Clean up, filter, map labels, and deduplicate by text
            clause['entities'] = []
            seen_texts = set()
            for entity in entities:
                score = float(entity.get('score', 0.0))
                text = entity.get('word', '').strip()
                group = entity.get('entity_group', '')
                if not text:
                    continue
                if score < CONFIDENCE_THRESHOLD:
                    continue
                key = text.lower()
                if key in seen_texts:
                    continue
                seen_texts.add(key)

                mapped_group = LABEL_MAP.get(group, group)
                clause['entities'].append({
                    "entity_type": mapped_group,
                    "confidence": float(round(score, 4)),
                    "text": text,
                })
        
        # 5. Save the final, enriched data
        with open(OUTPUT_CLAUSES_FILE, 'w', encoding='utf-8') as f:
            json.dump(clauses, f, indent=4)
        
        print(f"\nSuccess! Enriched clauses saved to '{OUTPUT_CLAUSES_FILE}'")

        # Display a sample of the final result
        print("\n--- Example Output (First Clause) ---")
        print(json.dumps(clauses[0], indent=2))