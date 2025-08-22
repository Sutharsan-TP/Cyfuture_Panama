"""OCR ingestion: accepts image or PDF, extracts text, and saves to Documents/*.txt
Auto-detects Tesseract path from env or default Windows install and creates output folders.
For PDFs: extracts digital text via PyMuPDF; if none, rasterizes pages and OCRs.
"""
import os
from PIL import Image
import pytesseract
import dotenv
import fitz  # PyMuPDF
import argparse

# Optional Gemini fallback
from typing import Optional
try:
    from gemini_ocr import ocr_with_gemini  # local helper that uses google-generativeai
except Exception:
    ocr_with_gemini = None  # Will check at runtime

# Load environment variables (e.g., TESSERACT_PATH)
dotenv.load_dotenv()

# Configure Tesseract path if provided
_tess_from_env = os.getenv("TESSERACT_PATH")
_tess_default_win = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
if _tess_from_env and os.path.isfile(_tess_from_env):
    pytesseract.pytesseract.tesseract_cmd = _tess_from_env
elif os.path.isfile(_tess_default_win):
    pytesseract.pytesseract.tesseract_cmd = _tess_default_win

def ocr_image(image_path: str) -> str:
    if not os.path.exists(image_path):
        return f"Error: File not found at {image_path}"

    try:
        # Validate Tesseract is reachable early
        _ = pytesseract.get_tesseract_version()
        img = Image.open(image_path)

        extracted_text = pytesseract.image_to_string(img)
        
        return extracted_text
    except pytesseract.TesseractNotFoundError as e:
        # Attempt fallback to Gemini if enabled
        if os.getenv("FALLBACK_TO_GEMINI", "true").lower() == "true" and ocr_with_gemini:
            return ocr_with_gemini(image_path)
        return (
            "Error: Tesseract OCR is not installed or not found. "
            "Install it and/or set TESSERACT_PATH in .env to the full path of tesseract.exe. "
            f"Details: {e}"
        )
    except Exception as e:
        # General failure; optionally fallback
        if os.getenv("FALLBACK_TO_GEMINI", "true").lower() == "true" and ocr_with_gemini:
            try:
                return ocr_with_gemini(image_path)
            except Exception as ge:
                return f"An error occurred during OCR (and Gemini fallback failed): {ge}"
        return f"An error occurred during OCR: {e}"


def _pixmap_to_pil(pix: "fitz.Pixmap") -> Image.Image:
    mode = "RGB" if pix.n < 4 else "RGBA"
    return Image.frombytes(mode, [pix.width, pix.height], pix.samples)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF. If digital text is empty, OCR the rasterized pages."""
    if not os.path.exists(pdf_path):
        return f"Error: File not found at {pdf_path}"

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return f"Error opening PDF: {e}"

    # 1) Try digital text extraction
    texts = []
    try:
        for page in doc:
            texts.append(page.get_text("text") or "")
    except Exception as e:
        texts = []
    digital_text = "\n".join(t.strip() for t in texts if t)

    if digital_text.strip():
        return digital_text

    # 2) Fallback to OCR per page (rasterize at 200 DPI equivalent)
    ocr_texts = []
    try:
        zoom = 2.0  # ~ 144-192 DPI depending on source; adjust for quality/speed
        mat = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = _pixmap_to_pil(pix)
            try:
                _ = pytesseract.get_tesseract_version()
                ocr_texts.append(pytesseract.image_to_string(img))
            except pytesseract.TesseractNotFoundError:
                if os.getenv("FALLBACK_TO_GEMINI", "true").lower() == "true" and ocr_with_gemini:
                    # Save temp image to path-like buffer for Gemini helper
                    # Simpler: re-use page rasterization by saving to a temp PNG
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
                        img.save(tmp.name)
                        ocr_texts.append(ocr_with_gemini(tmp.name))
                else:
                    ocr_texts.append("[OCR unavailable: Tesseract not found]")
    except Exception as e:
        return f"An error occurred during PDF OCR: {e}"

    return "\n".join(ocr_texts)


def ocr_document(file_path: str) -> str:
    """Unified OCR for image or PDF path."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
        return ocr_image(file_path)
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    return "Error: Unsupported file type. Provide an image or PDF."

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR ingestion for image/PDF")
    parser.add_argument(
        "--file",
        dest="input_file",
        type=str,
        default=os.path.join("Documents", "sample_contract.png"),
        help="Path to input image or PDF",
    )
    args = parser.parse_args()

    file_path = args.input_file
    print(f"Starting OCR process for: {file_path}")

    # Call the function to get the text
    text = ocr_document(file_path)

    print("\n" + "=" * 50)
    print("                OCR EXTRACTION COMPLETE")
    print("=" * 50 + "\n")

    # Print the first 500 characters of the result
    print(text[:500])

    # Save the full extracted text to Documents/<basename>.txt
    document_folder = "Documents"
    base = os.path.splitext(os.path.basename(file_path))[0]
    output_filename = base + ".txt"
    output_path = os.path.join(document_folder, output_filename)
    os.makedirs(document_folder, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"\n--- Full text saved to: {output_path} ---")