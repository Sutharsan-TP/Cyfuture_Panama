# Dynamite Legal AI — Contract Intelligence Pipeline

A fast, end‑to‑end pipeline that turns unstructured contracts (images or PDFs) into structured insights: OCR → Clause Segmentation → Entity Extraction (NER) → Summarization & Risk Analysis.

## 1) Problem & Why Now
Contracts are long, inconsistent, and costly to review. Legal teams need quick, reliable summaries, key term extraction, and risk flags. With modern LLMs and optimized inference, we can automate the heavy lifting while keeping humans in the loop.

## 2) What It Does
- Accepts images or PDFs and extracts text (OCR)
- Splits contracts into clean, titled clauses (segmentation)
- Extracts entities using a quantized transformer NER model
- Produces an executive summary, key terms, risks with severities, and recommendations
- Outputs machine‑readable JSON and a human‑readable Markdown report

## 3) Architecture Overview
Pipeline (ETL + AI):
1. Ingestion (OCR)
   - Primary: Tesseract (local OCR)
   - Fallback: Google Gemini 1.5 (multimodal OCR) when Tesseract is missing/blocked
   - PDF handling:
     - If digital text exists → extract directly (PyMuPDF)
     - If scanned → rasterize pages and OCR
2. Segmentation (LLM)
   - Google Gemini 1.5 Flash prompts return a strict JSON list of clauses
3. NER (Optimized)
   - Hugging Face transformers + Optimum + ONNX Runtime
   - Model: `dslim/bert-base-NER` (public)
   - Export to ONNX and dynamic INT8 quantization for speed
   - Post‑processing: confidence filter, dedupe, basic label mapping
4. Analysis (LLM)
   - Gemini 1.5 Flash generates: executive summary, key terms, risks (with severities and rationales), recommendations, open questions
   - Returns strict JSON and a Markdown report

Core files:
- `ingestion.py` — OCR (image/PDF), Tesseract + Gemini fallback
- `segmentation.py` — Gemini‑based clause segmentation
- `run_ner_pipeline.py` — ONNX export/quantize + NER + post‑processing
- `analysis.py` — Summarization + risk analysis
- `gemini_ocr.py` — Standalone Gemini OCR helper
- `run_all.py` — One‑command runner for the full pipeline

## 4) Tech Stack & Components
- Python
- OCR: Tesseract (pytesseract), PyMuPDF (PDF text/rasterize), Gemini 1.5 (fallback)
- LLMs: Google Generative AI (gemini‑1.5‑flash)
- NER: Hugging Face transformers + Optimum + ONNX Runtime + Torch
- Utilities: Pillow, python‑dotenv, huggingface_hub

Dependencies (see `requirements.txt`):
- `transformers`, `optimum`, `onnx`, `onnxruntime`, `torch`
- `pillow`, `pytesseract`, `pymupdf`
- `google-generativeai`, `python-dotenv`, `huggingface_hub`

## 5) Setup
1. Python env
   - Python 3.10+ recommended
   - `pip install -r requirements.txt`
2. Tesseract (optional but recommended for local OCR)
   - Install Windows x64 setup from the official release
   - Add install path to `PATH` or `.env` as `TESSERACT_PATH`
3. Environment variables (`.env`)
   - `GOOGLE_API_KEY=...`
   - `HUGGINGFACEHUB_API_TOKEN=` (optional for gated models)
   - `TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe` (optional)
   - `FALLBACK_TO_GEMINI=true`
   - See `.env.example` for a template

## 6) How To Run
Option A — one command (auto‑detects image/PDF):
- `python run_all.py --file Documents/sample_contract.png`
- `python run_all.py --file Documents/sample_contract.pdf`

Option B — step by step:
- `python ingestion.py --file Documents/sample_contract.pdf`
- `python segmentation.py --input Documents/sample_contract.txt --output documents/segmented_clauses.json`
- `python run_ner_pipeline.py`
- `python analysis.py`

Outputs:
- `Documents/*.txt` — OCR text
- `documents/segmented_clauses.json` — clauses
- `documents/clauses_with_entities.json` — NER results
- `documents/summary_and_risks.{json,md}` — final report

## 7) Demo Notes & Known Warnings
- Windows may show ONNX exporter or symlink cache warnings — harmless for the demo
- Some gRPC/GLOG warnings may appear from SDKs — we suppress where practical
- Template placeholders (e.g., `[number]`) in OCR’d text reflect the source; use a finalized contract for richer extraction

## 8) Results (Example)
- End‑to‑end pipeline completes in seconds to a few minutes depending on model download and OCR complexity
- Clean clause structure, general NER labels (PERSON/ORG/LOCATION/OTHER), and a structured risk report

## 9) Roadmap
- UI: simple web app for file upload, review, and approval workflow
- Legal‑specific NER: swap to a public legal NER or fine‑tune on CUAD/industry data
- Term extraction: rule‑based/ML extractors for dates, durations, amounts
- Vector search: clause retrieval and cross‑document comparisons
- Redlines & drafting: suggested edits for risky clauses
- Evaluations: add golden set and quality metrics; pin dependency versions for reproducibility

## 10) Responsible AI & Privacy
- No sensitive data should be logged or committed (see `.gitignore`)
- `.env` and keys are local; use secure key vaults in production
- Gemini usage may incur cost; restrict via API key scoping

## 11) Team & Time (Hackathon)
- Built as a pragmatic, modular stack to demo value fast
- Clear seams between OCR, segmentation, NER, and analysis for future ownership

---
Questions or a quick live demo? Run `python run_all.py --file <your_contract>` and open the Markdown report in `documents/`.
