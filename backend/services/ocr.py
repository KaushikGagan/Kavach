"""
OCR Document Verification Service
Uses EasyOCR (PyTorch-based, no Tesseract install needed).

Pipeline:
  1. Preprocess image (grayscale + threshold + denoise)
  2. Run EasyOCR to extract all text
  3. Clean and normalize extracted text
  4. Match against user-provided name
  5. Return score + extracted fields

Lazy-loads EasyOCR reader on first call (avoids startup delay).
"""
import cv2
import numpy as np
import re
import base64
from typing import Optional
from layers.utils import to_python

# Lazy-loaded reader — initialized once on first OCR call
_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr
        # English only, GPU=False for compatibility
        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _reader


def _b64_to_img(b64: str) -> Optional[np.ndarray]:
    if "," in b64:
        b64 = b64.split(",")[1]
    arr = np.frombuffer(base64.b64decode(b64), np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _preprocess(img: np.ndarray) -> np.ndarray:
    """
    Preprocess ID image for better OCR accuracy:
    1. Upscale small images (OCR works better on larger images)
    2. Convert to grayscale
    3. CLAHE for contrast enhancement
    4. Adaptive threshold to handle uneven lighting
    5. Denoise
    """
    # Upscale if too small
    h, w = img.shape[:2]
    if w < 800:
        scale = 800 / w
        img   = cv2.resize(img, (int(w * scale), int(h * scale)),
                           interpolation=cv2.INTER_CUBIC)

    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray  = clahe.apply(gray)

    # Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10)

    # Adaptive threshold — handles shadows and uneven lighting on ID cards
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )

    return thresh


def _clean_text(text: str) -> str:
    """Remove noise characters, normalize whitespace."""
    # Remove non-alphanumeric except spaces and common punctuation
    text = re.sub(r"[^a-zA-Z0-9\s/\-\.]", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text.lower()


def _normalize_name(name: str) -> str:
    """Normalize name for comparison: lowercase, remove spaces/punctuation."""
    return re.sub(r"[^a-z]", "", name.lower())


def _extract_name_from_text(text: str) -> Optional[str]:
    """
    Heuristic name extraction from ID document text.
    Looks for patterns common in Indian IDs (Aadhaar, PAN, Passport):
    - Line after "name:" label
    - All-caps words (common in IDs)
    - Lines with 2-4 words that look like a person's name
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Pattern 1: Line explicitly labeled "name"
    for i, line in enumerate(lines):
        if re.search(r"\bname\b", line.lower()) and i + 1 < len(lines):
            candidate = lines[i + 1].strip()
            if 2 <= len(candidate.split()) <= 5:
                return candidate

    # Pattern 2: All-caps line with 2-6 words (common in Aadhaar/PAN/Passport)
    for line in lines:
        words = line.split()
        if 2 <= len(words) <= 6 and all(w.isupper() and w.isalpha() for w in words):
            return line

    # Pattern 3: Title-case line with 2-6 words
    for line in lines:
        words = line.split()
        if 2 <= len(words) <= 6 and all(w.istitle() and w.isalpha() for w in words):
            return line

    # Pattern 4: Mixed case line that looks like a name (no digits, 2-6 words)
    for line in lines:
        words = line.split()
        if 2 <= len(words) <= 6 and all(w.isalpha() and len(w) >= 2 for w in words):
            return line

    return None


def extract_text(image_b64: str) -> dict:
    """
    Run OCR on ID image and return extracted text + fields.
    """
    img = _b64_to_img(image_b64)
    if img is None:
        return to_python({"success": False, "raw_text": "",
                          "clean_text": "", "extracted_name": None,
                          "detail": "Could not decode image"})

    try:
        processed = _preprocess(img)
        reader    = _get_reader()

        # EasyOCR returns list of (bbox, text, confidence)
        results   = reader.readtext(processed, detail=True, paragraph=False)

        # Filter by confidence > 0.3 to reduce noise
        raw_lines = [text for (_, text, conf) in results if conf > 0.3]
        raw_text  = "\n".join(raw_lines)
        clean     = _clean_text(raw_text)

        extracted_name = _extract_name_from_text(raw_text)

        return to_python({
            "success":        True,
            "raw_text":       raw_text[:500],   # cap for JSON size
            "clean_text":     clean[:500],
            "extracted_name": extracted_name,
            "word_count":     len(clean.split()),
            "detail": f"OCR extracted {len(raw_lines)} text regions, name={'found' if extracted_name else 'not found'}",
        })

    except Exception as e:
        return to_python({
            "success":        False,
            "raw_text":       "",
            "clean_text":     "",
            "extracted_name": None,
            "detail":         f"OCR error: {str(e)[:100]}",
        })


def match_name(ocr_result: dict, expected_name: str) -> dict:
    """
    Compare OCR-extracted name against user-provided name.
    Handles long Indian names with multiple parts.
    """
    if not ocr_result.get("success") or not expected_name:
        return to_python({
            "matched":   False,
            "ocr_score": 40,
            "method":    "skipped",
            "detail":    "OCR failed or no name provided",
        })

    norm_expected = _normalize_name(expected_name)
    clean_text    = _normalize_name(ocr_result.get("clean_text", ""))
    extracted     = ocr_result.get("extracted_name")

    # Method 1: Exact name field match
    if extracted:
        norm_extracted = _normalize_name(extracted)
        if norm_expected == norm_extracted:
            return to_python({"matched": True, "ocr_score": 100,
                              "method": "exact_name_field",
                              "detail": f"Name field exact match: '{extracted}'"})
        if norm_expected in norm_extracted or norm_extracted in norm_expected:
            return to_python({"matched": True, "ocr_score": 85,
                              "method": "partial_name_field",
                              "detail": f"Name field partial match: '{extracted}'"})

    # Method 2: Full name in OCR text
    if len(norm_expected) >= 4 and norm_expected in clean_text:
        return to_python({"matched": True, "ocr_score": 80,
                          "method": "text_contains_name",
                          "detail": "Full name found in document text"})

    # Method 3: Individual name parts (handles long Indian names)
    # Split into parts, require majority to match
    name_parts = [p for p in norm_expected.split() if len(p) >= 3]
    if name_parts:
        matched_parts = [p for p in name_parts if p in clean_text]
        ratio = len(matched_parts) / len(name_parts)
        if ratio >= 0.6:  # 60% of name parts found
            score = int(55 + ratio * 30)
            return to_python({"matched": True, "ocr_score": score,
                              "method": "name_parts_match",
                              "detail": f"{len(matched_parts)}/{len(name_parts)} name parts found in document"})
        if ratio >= 0.4:  # At least 40% found — weak match
            return to_python({"matched": False, "ocr_score": 45,
                              "method": "weak_name_parts",
                              "detail": f"Only {len(matched_parts)}/{len(name_parts)} name parts found"})

    # Method 4: Any single significant name part (>=5 chars) found
    long_parts = [p for p in name_parts if len(p) >= 5]
    if long_parts and any(p in clean_text for p in long_parts):
        found = [p for p in long_parts if p in clean_text]
        return to_python({"matched": False, "ocr_score": 50,
                          "method": "partial_name_found",
                          "detail": f"Partial name match: {found[0]} found in document"})

    return to_python({
        "matched":   False,
        "ocr_score": 40,
        "method":    "no_match",
        "detail":    f"Name '{expected_name}' not found in document — check spelling or ID quality",
    })


def verify_document(image_b64: str, expected_name: str = "") -> dict:
    """
    Full document verification pipeline:
    1. Extract text via OCR
    2. Match name if provided
    3. Return combined result
    """
    ocr_result   = extract_text(image_b64)
    name_result  = match_name(ocr_result, expected_name) if expected_name else \
                   to_python({"matched": False, "ocr_score": 50,
                              "method": "no_name_provided",
                              "detail": "No expected name provided — OCR text extracted only"})

    # Document quality check: if very few words extracted, likely bad image
    word_count   = ocr_result.get("word_count", 0)
    doc_readable = word_count >= 5

    status = "PASS" if (name_result["matched"] and doc_readable) else \
             ("WARN" if doc_readable else "FAIL")

    return to_python({
        "status":         status,
        "ocr_match":      name_result["matched"],
        "ocr_score":      name_result["ocr_score"],
        "extracted_name": ocr_result.get("extracted_name"),
        "doc_readable":   doc_readable,
        "word_count":     word_count,
        "match_method":   name_result["method"],
        "detail":         name_result["detail"],
        "ocr_detail":     ocr_result["detail"],
    })
