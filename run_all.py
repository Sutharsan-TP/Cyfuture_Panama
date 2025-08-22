"""End-to-end runner: OCR -> Segmentation -> NER -> Analysis.
Accepts --file path to image or PDF; derives text path automatically.
"""
import subprocess
import sys
import argparse
import os

parser = argparse.ArgumentParser(description="Run full contract pipeline")
parser.add_argument(
    "--file",
    dest="input_file",
    type=str,
    default=os.path.join("Documents", "sample_contract.png"),
    help="Path to input image or PDF",
)
args = parser.parse_args()

input_file = args.input_file
base = os.path.splitext(os.path.basename(input_file))[0]
txt_path = os.path.join("Documents", base + ".txt")

steps = [
    ("OCR (ingestion)", [sys.executable, "ingestion.py", "--file", input_file]),
    ("Segmentation", [sys.executable, "segmentation.py", "--input", txt_path, "--output", "documents/segmented_clauses.json"]),
    ("NER", [sys.executable, "run_ner_pipeline.py"]),
    ("Analysis", [sys.executable, "analysis.py"]),
]

for name, cmd in steps:
    print(f"\n=== Running: {name} ===")
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        print(f"Step failed: {name} (exit {proc.returncode})")
        sys.exit(proc.returncode)

print("\nPipeline complete. Outputs in documents/ and Documents/")
