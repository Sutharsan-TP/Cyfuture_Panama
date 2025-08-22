"""OCR using Google Gemini 1.5 (multimodal) to extract text from an image.
Requires GOOGLE_API_KEY in your .env. Outputs plain text.
"""
import os
from pathlib import Path
from typing import Optional

import dotenv
import google.generativeai as genai
from PIL import Image


def _configure_gemini() -> Optional[str]:
    dotenv.load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "Missing GOOGLE_API_KEY in environment/.env"
    genai.configure(api_key=api_key)
    return None


def ocr_with_gemini(image_path: str) -> str:
    if not os.path.exists(image_path):
        return f"Error: File not found at {image_path}"

    err = _configure_gemini()
    if err:
        return f"Error: {err}"

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        img = Image.open(image_path)
        prompt = (
            "Extract all legible text from this image. Return plain text only, "
            "preserving reading order as best as possible."
        )
        resp = model.generate_content([prompt, img])
        text = (resp.text or "").strip()
        return text if text else ""
    except Exception as e:
        return f"An error occurred while using Gemini OCR: {e}"


if __name__ == "__main__":
    # Example usage mirroring ingestion.py defaults
    documents_dir = Path("Documents")
    image_name = "sample_contract.png"
    output_name = "sample_contract.txt"

    image_path = documents_dir / image_name
    output_path = documents_dir / output_name
    documents_dir.mkdir(parents=True, exist_ok=True)

    print(f"Using Gemini OCR for: {image_path}")
    text = ocr_with_gemini(str(image_path))

    # Show a short preview
    preview = text[:500] if isinstance(text, str) else str(text)
    print("\n--- OCR PREVIEW (first 500 chars) ---\n" + preview)

    # Save to file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nSaved OCR text to: {output_path}")
    except Exception as e:
        print(f"Failed to save OCR text: {e}")
