# In a new script, e.g., 'quantize_model.py'
from optimum.onnxruntime import ORTModelForTokenClassification
from optimum.onnxruntime import ORTQuantizer
from optimum.onnxruntime.configuration import QuantizationConfig
from pathlib import Path

model_id = "zlucia/cuad-roberta-base-ner"
onnx_path = "onnx-models/cuad-ner-base"

# This one-liner loads the model from the Hub and exports it to the ONNX format.
model = ORTModelForTokenClassification.from_pretrained(model_id, export=True)

# Save the exported model
model.save_pretrained(onnx_path)

print(f"Model exported to ONNX format at: {onnx_path}")

# The file to be quantized
onnx_model_path = Path(onnx_path) / "model.onnx"

# The location to save the quantized model
quantized_model_path = Path(onnx_path) / "model_quantized.onnx"

# Create a quantizer for our model
quantizer = ORTQuantizer.from_pretrained(onnx_path)

# Define the dynamic quantization configuration
dqconfig = QuantizationConfig(
    is_static=False, # Use dynamic quantization
    format="QOperator",
    mode="dynamic",
    activations_dtype="uint8",
    weights_dtype="int8",
    per_channel=True,
    op_types_to_quantize=["MatMul", "Add"]
)

# Apply quantization
quantizer.quantize(
    save_dir=onnx_path,
    quantization_config=dqconfig,
    file_suffix="_quantized" # this will create model_quantized.onnx
)

print(f"Quantized model saved to: {quantized_model_path}")