# In your main script, e.g., 'ner_extraction_quantized.py'
import json
from transformers import pipeline, AutoTokenizer
from optimum.onnxruntime import ORTModelForTokenClassification

# 1. Define paths and load data
quantized_model_dir = "onnx-models/cuad-ner-base"
clauses_file = "documents/clauses_with_entities.json" # Or your segmented clauses file

with open(clauses_file, 'r', encoding='utf-8') as f:
    clauses = json.load(f)

# 2. Load the quantized model and the tokenizer
print("Loading quantized model and tokenizer...")
model = ORTModelForTokenClassification.from_pretrained(quantized_model_dir, file_name="model_quantized.onnx")
tokenizer = AutoTokenizer.from_pretrained(quantized_model_dir)

# 3. Create the NER pipeline with the quantized model
print("Creating NER pipeline...")
ner_pipeline = pipeline(
    "token-classification",
    model=model,
    tokenizer=tokenizer,
    aggregation_strategy="simple"
)

# 4. Run inference (this will be faster now)
print("Running inference on the first clause...")
first_clause_text = clauses[0]['clause_text']
entities = ner_pipeline(first_clause_text)

print("\n--- Entities from Quantized Model ---")
for entity in entities:
    print(f"  - Entity: {entity['word']}, Type: {entity['entity_group']}, Score: {round(entity['score'], 4)}")