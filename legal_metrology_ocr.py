"""
Label-anchored extraction pipeline for Legal Metrology compliance checking.

Pipeline:

    Image
      |
      v
    PaddleOCR
      |
      |-- individual OCR boxes
      |-- polygon
      |-- angle
      |-- OCR confidence
      |
      v
    Geometry-based deterministic extraction
      |
      v
    Gemini visual second-pass validation
      |
      |-- verify OCR candidate
      |-- correct OCR candidate
      |-- recover missing fields
      |-- detect label/value mismatch
      |
      v
    Evidence reconciliation
      |
      v
    Final compliance evaluator

IMPORTANT:
Gemini does NOT decide legal compliance.
Gemini validates the visual facts extracted from the image.
Python makes the final compliance decision.
"""

import os
import re
import math
import json
import base64
import cv2
import numpy as np

from rapidfuzz import fuzz
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# PaddleOCR
# ---------------------------------------------------------------------

os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
load_dotenv()

from paddleocr import PaddleOCR


# ---------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------

from google import genai
from pydantic import BaseModel, Field
from typing import Optional, Dict


# ================================================================
# CONFIGURATION
# ================================================================

GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print(
        "WARNING: GEMINI_API_KEY is not set. "
        "Gemini validation will be disabled."
    )

gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


# ---------------------------------------------------------------------
# PaddleOCR initialization
# ---------------------------------------------------------------------

_DOC_ORIENTATION_SUPPORTED = True

try:
    ocr = PaddleOCR(
        use_textline_orientation=True,
        use_doc_orientation_classify=True,
        use_doc_unwarping=False,
        lang="en",
        enable_mkldnn=False,
        det_db_unclip_ratio=1.8,
        det_db_thresh=0.25,
    )

except TypeError:

    _DOC_ORIENTATION_SUPPORTED = False

    ocr = PaddleOCR(
        use_textline_orientation=True,
        lang="en",
        enable_mkldnn=False,
        det_db_unclip_ratio=1.8,
        det_db_thresh=0.25,
    )


# ================================================================
# GEMINI STRUCTURED RESPONSE
# ================================================================

class GeminiFieldResult(BaseModel):
    declared: bool = Field(
        description="Whether this field is visibly present on the package."
    )
    value: Optional[str] = Field(
        default=None,
        description=(
            "The exact visually readable value associated with the field. "
            "Return null if there is no direct value or it cannot be read."
        ),
    )
    pointer_location: Optional[str] = Field(
        default=None,
        description=(
            "If the package states the value is printed elsewhere "
            "(e.g., 'SEE TOP OF PACK', 'FOR B.NO, PKD & EXP SEE CRIMP/BOTTOM'), "
            "record that exact location phrase here. Otherwise null."
        ),
    )
    verified: bool = Field(
        description=(
            "True only if the supplied OCR candidate agrees with "
            "the image or Gemini independently confirms the field/pointer."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Visual confidence from 0 to 1."
    )
    correction: Optional[str] = Field(
        default=None,
        description="Corrected value if the OCR candidate is wrong. Otherwise null."
    )
    evidence: str = Field(
        description=(
            "Short explanation describing what is visibly present "
            "and how the label/value/pointer was verified."
        )
    )

class GeminiValidationResult(BaseModel):

    mrp: GeminiFieldResult

    net_quantity: GeminiFieldResult

    unit_sale_price: GeminiFieldResult

    mfg_date: GeminiFieldResult

    expiry: GeminiFieldResult

    manufacturer: GeminiFieldResult

    consumer_care: GeminiFieldResult


# ================================================================
# 1. PREPROCESSING
# ================================================================

def preprocess_label_image(image_path):

    img = cv2.imread(image_path)

    if img is None:
        raise FileNotFoundError(
            f"Could not read image: {image_path}"
        )

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    contrast_img = clahe.apply(gray)

    processed_img = cv2.bilateralFilter(
        contrast_img,
        d=9,
        sigmaColor=75,
        sigmaSpace=75
    )

    return (
        cv2.cvtColor(
            processed_img,
            cv2.COLOR_GRAY2BGR
        ),
        img
    )


# ================================================================
# 2. BOX GEOMETRY
# ================================================================

def box_center(poly):

    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]

    return (
        sum(xs) / len(xs),
        sum(ys) / len(ys)
    )


def box_angle(poly):
    """
    Angle of first long-ish edge.

    0 degrees = horizontal.
    """

    p0, p1 = poly[0], poly[1]

    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]

    return math.degrees(
        math.atan2(dy, dx)
    )


# ================================================================
# 3. DESKEW + RE-READ
# ================================================================

def deskew_and_reread(image, poly):

    pts = np.array(
        poly,
        dtype="float32"
    )

    width = int(
        max(
            np.linalg.norm(pts[0] - pts[1]),
            np.linalg.norm(pts[2] - pts[3])
        )
    )

    height = int(
        max(
            np.linalg.norm(pts[1] - pts[2]),
            np.linalg.norm(pts[3] - pts[0])
        )
    )

    if width <= 0 or height <= 0:
        return ""

    dst = np.array(
        [
            [0, 0],
            [width, 0],
            [width, height],
            [0, height],
        ],
        dtype="float32"
    )

    M = cv2.getPerspectiveTransform(
        pts,
        dst
    )

    warped = cv2.warpPerspective(
        image,
        M,
        (width, height)
    )

    # Vertical text.
    if height > width:
        warped = cv2.rotate(
            warped,
            cv2.ROTATE_90_CLOCKWISE
        )

    warped = cv2.resize(
        warped,
        None,
        fx=2.5,
        fy=2.5,
        interpolation=cv2.INTER_CUBIC
    )

    result = ocr.predict(warped)

    texts = []

    for res in result:

        if "rec_texts" in res:
            texts.extend(
                res["rec_texts"]
            )

    return " ".join(texts).strip()


# ================================================================
# 4. WHOLE-PAGE ORIENTATION
# ================================================================

def _quick_angle_probe(image):

    results = ocr.predict(image)

    angles = []

    for res in results:

        polys = (
            res.get("rec_polys")
            or res.get("dt_polys")
        )

        if polys is None:
            continue

        for poly in polys:

            angles.append(
                box_angle(poly)
            )

    if not angles:
        return 0

    buckets = [0, 90, 180, 270]

    bucket_counts = {
        b: 0
        for b in buckets
    }

    for a in angles:

        a_norm = a % 360

        nearest = min(
            buckets,
            key=lambda b:
                min(
                    abs(a_norm - b),
                    360 - abs(a_norm - b)
                )
        )

        bucket_counts[nearest] += 1

    dominant = max(
        bucket_counts,
        key=bucket_counts.get
    )

    if (
        bucket_counts[dominant]
        / len(angles)
        >= 0.6
    ):
        return dominant

    return 0


def _rotate_image(image, degrees):

    if degrees == 0:
        return image

    rot_map = {
        90: cv2.ROTATE_90_CLOCKWISE,
        180: cv2.ROTATE_180,
        270: cv2.ROTATE_90_COUNTERCLOCKWISE,
    }

    return cv2.rotate(
        image,
        rot_map[degrees]
    )


def correct_page_orientation(clean_img):

    rotation = _quick_angle_probe(
        clean_img
    )

    if rotation != 0:

        undo = {
            90: 270,
            180: 180,
            270: 90,
        }[rotation]

        return (
            _rotate_image(
                clean_img,
                undo
            ),
            rotation
        )

    return clean_img, 0


# ================================================================
# 5. OCR WITH BOXES
# ================================================================

def run_ocr_with_boxes(image_path):

    clean_img, orig_img = (
        preprocess_label_image(
            image_path
        )
    )

    if not _DOC_ORIENTATION_SUPPORTED:

        clean_img, detected_rotation = (
            correct_page_orientation(
                clean_img
            )
        )

        if detected_rotation != 0:

            orig_img = _rotate_image(
                orig_img,
                {
                    90: 270,
                    180: 180,
                    270: 90
                }[detected_rotation]
            )

    results = ocr.predict(
        clean_img
    )

    boxes = []

    for res in results:

        polys = (
            res.get("rec_polys")
            or res.get("dt_polys")
        )

        texts = res.get(
            "rec_texts",
            []
        )

        scores = res.get(
            "rec_scores",
            [1.0] * len(texts)
        )

        if polys is None:
            continue

        for poly, text, score in zip(
            polys,
            texts,
            scores
        ):

            angle = box_angle(poly)

            entry = {
                "text": str(text),
                "poly": [
                    [
                        float(p[0]),
                        float(p[1])
                    ]
                    for p in poly
                ],
                "center": box_center(poly),
                "angle": float(angle),
                "score": float(score),
            }

            # Re-read rotated low-confidence boxes.
            if (
                abs(angle) > 20
                and score < 0.85
            ):

                reread = deskew_and_reread(
                    orig_img,
                    poly
                )

                if reread:

                    entry["text"] = reread
                    entry["reread"] = True

            boxes.append(entry)

    return boxes


# ================================================================
# 6. LABEL KEYWORDS
# ================================================================

LABEL_KEYWORDS = {

    "mrp": [
        "MRP",
        "M.R.P",
        "Maximum Retail Price",
    ],

    "net_qty": [
        "Net Quantity",
        "Net Qty",
        "Net Wt",
        "Net Weight",
    ],

    "usp": [
        "USP",
        "Unit Sale Price",
        "Per g",
        "Per kg",
        "Per ml",
    ],

    "mfg_date": [
        "Mfd",
        "Mfg Date",
        "Pkd",
        "Packed on",
        "Packing Date",
        "Date of Mfg",
    ],

    "expiry": [
        "Use By",
        "Best Before",
        "Expiry",
        "Exp Date",
    ],

    "manufacturer": [
        "Marketed By",
        "Manufactured By",
        "Mfg By",
        "Packed By",
    ],

    "consumer_care": [
        "Consumer Care",
        "Customer Care",
        "Feedback",
        "Toll Free",
        "Email",
    ],
}


# ================================================================
# 7. VALUE PATTERNS
# ================================================================

VALUE_PATTERNS = {

    "mrp":
        r'(?:₹|Rs\.?|INR)?\s*'
        r'([0-9]+(?:\.[0-9]{1,2})?)',

    "net_qty":
        r'([0-9]+(?:\.[0-9]+)?\s*'
        r'(?:g|kg|ml|l|gm|grams))',

    "date":
        r'([0-9]{1,2}'
        r'[/\-.]'
        r'[0-9]{1,2}'
        r'[/\-.]'
        r'[0-9]{2,4})',
}


# ================================================================
# 8. FUZZY LABEL MATCHING
# ================================================================

def find_label_box(
    boxes,
    keywords,
    min_score=70
):

    best = None
    best_score = 0

    for b in boxes:

        text = b["text"]

        for kw in keywords:

            text_score = fuzz.partial_ratio(
                kw.lower(),
                text.lower()
            )

            # Combine OCR confidence with
            # textual similarity.
            combined = (
                0.85 * text_score
                + 0.15 * (
                    b["score"] * 100
                )
            )

            if combined > best_score:

                best = b
                best_score = combined

    return (
        best
        if best_score >= min_score
        else None
    )


# ================================================================
# 9. PROXIMITY VALUE MATCHING
# ================================================================

def find_nearby_value(
    boxes,
    label_box,
    pattern,
    max_dist=250
):

    if label_box is None:
        return None

    # ----------------------------------------------------------
    # Same-box extraction
    # ----------------------------------------------------------

    m = re.search(
        pattern,
        label_box["text"],
        re.IGNORECASE
    )

    if m:
        return m.group(1)

    lx, ly = label_box["center"]

    candidates = []

    for b in boxes:

        if b is label_box:
            continue

        bx, by = b["center"]

        dist = math.hypot(
            bx - lx,
            by - ly
        )

        same_line = (
            abs(by - ly) < 40
        )

        below = (
            by > ly
            and abs(bx - lx) < 150
        )

        if (
            dist < max_dist
            and (same_line or below)
        ):
            candidates.append(
                (dist, b)
            )

    candidates.sort(
        key=lambda x: x[0]
    )

    for _, b in candidates:

        m = re.search(
            pattern,
            b["text"],
            re.IGNORECASE
        )

        if m:
            return m.group(1)

    return None


# ================================================================
# 10. COLUMN-RANK MATCHING
# ================================================================

def find_value_by_column_rank(
    boxes,
    label_box,
    pattern
):

    if (
        label_box is None
        or not boxes
    ):
        return None

    lx, ly = label_box["center"]

    band = [
        b for b in boxes
        if abs(
            b["center"][1] - ly
        ) < 400
    ]

    if len(band) < 2:
        return None

    xs = sorted(
        b["center"][0]
        for b in band
    )

    x_span = xs[-1] - xs[0]

    if x_span < 50:
        return None

    x_mid = (
        xs[0]
        + x_span * 0.5
    )

    left_col = sorted(
        [
            b for b in band
            if b["center"][0] < x_mid
        ],
        key=lambda b:
            b["center"][1]
    )

    right_col = sorted(
        [
            b for b in band
            if b["center"][0] >= x_mid
        ],
        key=lambda b:
            b["center"][1]
    )

    if (
        not left_col
        or not right_col
    ):
        return None

    try:

        rank = left_col.index(
            label_box
        )

    except ValueError:

        return None

    for offset in (
        0,
        1,
        -1,
        2
    ):

        idx = rank + offset

        if (
            0 <= idx
            < len(right_col)
        ):

            m = re.search(
                pattern,
                right_col[idx]["text"],
                re.IGNORECASE
            )

            if m:
                return m.group(1)

    return None


# ================================================================
# 11. DETERMINISTIC EXTRACTION
# ================================================================

def deterministic_extract(boxes):

    report = {

        "mrp_declared": False,
        "mrp_value": None,

        "net_quantity_declared": False,
        "net_quantity_value": None,

        "unit_sale_price_declared": False,

        "mfg_date_declared": False,
        "mfg_date_value": None,

        "expiry_or_use_by_declared": False,
        "expiry_value": None,

        "manufacturer_details_declared": False,

        "consumer_care_declared": False,

        "field_confidence": {},
    }

    def set_field(
        key_declared,
        key_value,
        label_key,
        pattern
    ):

        label_box = find_label_box(
            boxes,
            LABEL_KEYWORDS[label_key]
        )

        if label_box is None:

            report[
                "field_confidence"
            ][label_key] = {
                "status": "label_not_found"
            }

            return

        label_score = 0

        for kw in LABEL_KEYWORDS[label_key]:

            label_score = max(
                label_score,
                fuzz.partial_ratio(
                    kw.lower(),
                    label_box[
                        "text"
                    ].lower()
                )
            )

        if pattern:

            value = find_nearby_value(
                boxes,
                label_box,
                pattern
            )

            strategy = "proximity"

            if value is None:

                value = (
                    find_value_by_column_rank(
                        boxes,
                        label_box,
                        pattern
                    )
                )

                if value is not None:
                    strategy = "column-rank"

        else:

            value = "Present"
            strategy = "label-only"

        found = value is not None

        report[
            key_declared
        ] = found

        if key_value:
            report[
                key_value
            ] = value

        report[
            "field_confidence"
        ][label_key] = {

            "label_text":
                label_box["text"],

            "label_score":
                round(
                    label_score / 100,
                    3
                ),

            "ocr_score":
                round(
                    label_box["score"],
                    3
                ),

            "value":
                value,

            "strategy":
                strategy,

            "status":
                "found"
                if found
                else "value_not_found",
        }

    set_field(
        "mrp_declared",
        "mrp_value",
        "mrp",
        VALUE_PATTERNS["mrp"]
    )

    set_field(
        "net_quantity_declared",
        "net_quantity_value",
        "net_qty",
        VALUE_PATTERNS["net_qty"]
    )

    set_field(
        "unit_sale_price_declared",
        None,
        "usp",
        None
    )

    set_field(
        "mfg_date_declared",
        "mfg_date_value",
        "mfg_date",
        VALUE_PATTERNS["date"]
    )

    set_field(
        "expiry_or_use_by_declared",
        "expiry_value",
        "expiry",
        VALUE_PATTERNS["date"]
    )

    set_field(
        "manufacturer_details_declared",
        None,
        "manufacturer",
        None
    )

    set_field(
        "consumer_care_declared",
        None,
        "consumer_care",
        None
    )

    return report


# ================================================================
# 12. DETERMINE WHETHER GEMINI VALIDATION IS NEEDED
# ================================================================

def field_needs_gemini(
    report,
    field_name
):

    info = report[
        "field_confidence"
    ].get(
        field_name,
        {}
    )

    # Missing label.
    if not info:
        return True

    if info.get(
        "status"
    ) in (
        "label_not_found",
        "value_not_found",
    ):
        return True

    # Low OCR confidence.
    if info.get(
        "ocr_score",
        0
    ) < 0.85:
        return True

    # Weak fuzzy label match.
    if info.get(
        "label_score",
        0
    ) < 0.80:
        return True

    # Column-rank is more uncertain.
    if info.get(
        "strategy"
    ) == "column-rank":
        return True

    return False


# ================================================================
# 13. SERIALIZE OCR BOXES FOR GEMINI
# ================================================================

def serialize_boxes_for_gemini(boxes):

    output = []

    for i, b in enumerate(boxes):

        output.append({

            "id": i,

            "text":
                b["text"],

            "confidence":
                round(
                    b["score"],
                    3
                ),

            "angle":
                round(
                    b["angle"],
                    2
                ),

            "center": [
                round(
                    b["center"][0],
                    1
                ),
                round(
                    b["center"][1],
                    1
                )
            ],

            "polygon": [
                [
                    round(
                        p[0],
                        1
                    ),
                    round(
                        p[1],
                        1
                    )
                ]
                for p in b["poly"]
            ],

            "reread":
                bool(
                    b.get(
                        "reread",
                        False
                    )
                ),
        })

    return output


# ================================================================
# 14. GEMINI VALIDATION PROMPT
# ================================================================

def build_gemini_prompt(
    boxes,
    deterministic_report
):

    ocr_data = serialize_boxes_for_gemini(
        boxes
    )

    candidate_data = {

        "mrp": {
            "declared":
                deterministic_report[
                    "mrp_declared"
                ],
            "value":
                deterministic_report[
                    "mrp_value"
                ],
        },

        "net_quantity": {
            "declared":
                deterministic_report[
                    "net_quantity_declared"
                ],
            "value":
                deterministic_report[
                    "net_quantity_value"
                ],
        },

        "unit_sale_price": {
            "declared":
                deterministic_report[
                    "unit_sale_price_declared"
                ],
        },

        "mfg_date": {
            "declared":
                deterministic_report[
                    "mfg_date_declared"
                ],
            "value":
                deterministic_report[
                    "mfg_date_value"
                ],
        },

        "expiry": {
            "declared":
                deterministic_report[
                    "expiry_or_use_by_declared"
                ],
            "value":
                deterministic_report[
                    "expiry_value"
                ],
        },

        "manufacturer": {
            "declared":
                deterministic_report[
                    "manufacturer_details_declared"
                ],
        },

        "consumer_care": {
            "declared":
                deterministic_report[
                    "consumer_care_declared"
                ],
        },
    }

    return f"""
You are the SECOND visual validation layer for a packaged-product
label OCR system.

Your task is NOT to decide legal compliance.
Your task is to inspect the supplied package image and verify the
observable information printed on the package.

The original image is the source of truth.
The PaddleOCR extraction is only a hypothesis.

IMPORTANT RULES:
1. Carefully inspect the actual image.
2. Do not trust OCR blindly.
3. Do not invent information.
4. Do not infer a value that is not visually supported.
5. If text is blurry or genuinely unreadable, use null and lower confidence.
6. Verify that a value belongs to the correct label.
7. Pay special attention to:
   - MRP
   - Net Quantity
   - Unit Sale Price
   - Mfd / Mfg / Pkd
   - Use By / Best Before / Expiry
   - Manufacturer / Marketed By / Packed By
   - Consumer Care / Customer Care / Toll Free / Email
8. Check rotated, vertical and angled text.
9. If PaddleOCR is wrong, provide the corrected value.
10. If PaddleOCR missed a field, recover it if it is clearly visible.
11. POINTER HANDLING: If a mandatory field is declared on the label but directs 
    the consumer elsewhere (e.g., "SEE TOP OF PACK", "SEE BOTTOM", "FOR BATCH & PKD SEE CRIMP"):
    - Set "declared": true.
    - Set "pointer_location" to the printed phrase (e.g., "TOP OF PACK").
    - If the actual value is also clearly visible at that secondary location in the image, put it in "value".
    - If the secondary area is cut off/not captured in the image, set "value": null, but keep "declared": true and "verified": true. Do NOT treat this as missing or uncertain.
12. Do NOT make a legal conclusion.
13. "verified" means the candidate agrees with visible image evidence.
14. "confidence" must be between 0 and 1.

PADDLEOCR BOXES:
{json.dumps(ocr_data, ensure_ascii=False, indent=2)}

PADDLEOCR CANDIDATES:
{json.dumps(candidate_data, ensure_ascii=False, indent=2)}

Return only the required structured response.
"""


# ================================================================
# 15. GEMINI SECOND PASS
# ================================================================

def gemini_validate(
    image_path,
    boxes,
    deterministic_report
):

    if gemini_client is None:

        return {
            "enabled": False,
            "error":
                "GEMINI_API_KEY not configured",
        }

    prompt = build_gemini_prompt(
        boxes,
        deterministic_report
    )

    try:

        with open(
            image_path,
            "rb"
        ) as f:

            image_bytes = f.read()

        image_b64 = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        response = (
            gemini_client.models.generate_content(
                model=GEMINI_MODEL,

                contents=[
                    {
                        "text": prompt
                    },
                    {
                        "inline_data": {
                            "mime_type":
                                "image/jpeg",
                            "data":
                                image_b64,
                        }
                    },
                ],

                config={
                    "response_mime_type":
                        "application/json",

                    "response_schema":
                        GeminiValidationResult,
                },
            )
        )

        # Current SDK can expose structured
        # output through parsed.
        if getattr(
            response,
            "parsed",
            None
        ) is not None:

            parsed = response.parsed

            if isinstance(
                parsed,
                GeminiValidationResult
            ):
                result = parsed.model_dump()

            elif hasattr(
                parsed,
                "model_dump"
            ):
                result = parsed.model_dump()

            else:
                result = parsed

        else:

            result = json.loads(
                response.text
            )

        return {
            "enabled": True,
            "model": GEMINI_MODEL,
            "success": True,
            "result": result,
        }

    except Exception as e:

        return {
            "enabled": True,
            "model": GEMINI_MODEL,
            "success": False,
            "error": str(e),
        }


# ================================================================
# 16. FIELD RECONCILIATION
# ================================================================

def reconcile_field(paddle_declared, paddle_value, gemini_field):
    if not gemini_field:
        return {
            "declared": paddle_declared,
            "value": paddle_value,
            "source": "paddleocr",
            "status": "paddle_only",
        }

    gemini_declared = gemini_field.get("declared", False)
    gemini_value = gemini_field.get("value")
    pointer = gemini_field.get("pointer_location")
    correction = gemini_field.get("correction")
    gemini_confidence = float(gemini_field.get("confidence", 0))
    evidence = gemini_field.get("evidence", "")

    # 1. Field confirmed absent
    if not gemini_declared:
        return {
            "declared": False,
            "value": None,
            "source": "gemini",
            "status": "gemini_not_present",
            "gemini_confidence": gemini_confidence,
            "evidence": evidence,
        }

    # 2. Pointer detected (e.g., "SEE TOP OF PACK")
    if pointer:
        return {
            "declared": True,
            "value": gemini_value or f"Refer to: {pointer}",
            "pointer_location": pointer,
            "source": "gemini_pointer",
            "status": "declared_with_pointer",
            "gemini_confidence": gemini_confidence,
            "evidence": evidence,
        }

    # 3. Recovered by Gemini
    if paddle_value is None and gemini_value:
        return {
            "declared": True,
            "value": gemini_value,
            "source": "gemini_recovery",
            "status": "gemini_recovered",
            "gemini_confidence": gemini_confidence,
            "evidence": evidence,
        }

    # 4. Correction by Gemini
    if correction:
        return {
            "declared": True,
            "value": correction,
            "source": "gemini_correction",
            "status": "corrected_by_gemini",
            "paddle_value": paddle_value,
            "gemini_value": gemini_value,
            "gemini_confidence": gemini_confidence,
            "evidence": evidence,
        }

    # 5. Agreement
    if (
        paddle_value is not None
        and gemini_value is not None
        and normalize_value(paddle_value) == normalize_value(gemini_value)
    ):
        return {
            "declared": True,
            "value": paddle_value,
            "source": "paddleocr+gemini",
            "status": "verified",
            "paddle_value": paddle_value,
            "gemini_value": gemini_value,
            "gemini_confidence": gemini_confidence,
            "evidence": evidence,
        }

    # 6. Fallback conflict
    return {
        "declared": True,
        "value": None,
        "source": "conflict",
        "status": "uncertain",
        "paddle_value": paddle_value,
        "gemini_value": gemini_value,
        "gemini_confidence": gemini_confidence,
        "evidence": evidence,
    }

# ================================================================
# 17. NORMALIZATION FOR COMPARISON
# ================================================================

def normalize_value(value):

    if value is None:
        return ""

    value = str(value).strip().lower()

    value = value.replace(
        "₹",
        ""
    )

    value = value.replace(
        "rs.",
        ""
    )

    value = value.replace(
        "inr",
        ""
    )

    value = re.sub(
        r"\s+",
        "",
        value
    )

    return value


# ================================================================
# 18. FINAL RECONCILIATION
# ================================================================

def reconcile_results(
    paddle_report,
    gemini_response
):

    final = {}

    gemini_result = (
        gemini_response.get(
            "result"
        )
        if gemini_response
        and gemini_response.get(
            "success"
        )
        else None
    )

    if gemini_result is None:

        # Gemini unavailable.
        final.update({

            "mrp": {
                "declared":
                    paddle_report[
                        "mrp_declared"
                    ],
                "value":
                    paddle_report[
                        "mrp_value"
                    ],
                "source":
                    "paddleocr",
            },

            "net_quantity": {
                "declared":
                    paddle_report[
                        "net_quantity_declared"
                    ],
                "value":
                    paddle_report[
                        "net_quantity_value"
                    ],
                "source":
                    "paddleocr",
            },

            "unit_sale_price": {
                "declared":
                    paddle_report[
                        "unit_sale_price_declared"
                    ],
                "value":
                    None,
                "source":
                    "paddleocr",
            },

            "mfg_date": {
                "declared":
                    paddle_report[
                        "mfg_date_declared"
                    ],
                "value":
                    paddle_report[
                        "mfg_date_value"
                    ],
                "source":
                    "paddleocr",
            },

            "expiry": {
                "declared":
                    paddle_report[
                        "expiry_or_use_by_declared"
                    ],
                "value":
                    paddle_report[
                        "expiry_value"
                    ],
                "source":
                    "paddleocr",
            },

            "manufacturer": {
                "declared":
                    paddle_report[
                        "manufacturer_details_declared"
                    ],
                "value":
                    None,
                "source":
                    "paddleocr",
            },

            "consumer_care": {
                "declared":
                    paddle_report[
                        "consumer_care_declared"
                    ],
                "value":
                    None,
                "source":
                    "paddleocr",
            },
        })

        return final

    # ----------------------------------------------------------
    # Reconcile every field.
    # ----------------------------------------------------------

    final["mrp"] = reconcile_field(
        paddle_report[
            "mrp_declared"
        ],
        paddle_report[
            "mrp_value"
        ],
        gemini_result.get(
            "mrp"
        )
    )

    final["net_quantity"] = reconcile_field(
        paddle_report[
            "net_quantity_declared"
        ],
        paddle_report[
            "net_quantity_value"
        ],
        gemini_result.get(
            "net_quantity"
        )
    )

    final["unit_sale_price"] = reconcile_field(
        paddle_report[
            "unit_sale_price_declared"
        ],
        None,
        gemini_result.get(
            "unit_sale_price"
        )
    )

    final["mfg_date"] = reconcile_field(
        paddle_report[
            "mfg_date_declared"
        ],
        paddle_report[
            "mfg_date_value"
        ],
        gemini_result.get(
            "mfg_date"
        )
    )

    final["expiry"] = reconcile_field(
        paddle_report[
            "expiry_or_use_by_declared"
        ],
        paddle_report[
            "expiry_value"
        ],
        gemini_result.get(
            "expiry"
        )
    )

    final["manufacturer"] = reconcile_field(
        paddle_report[
            "manufacturer_details_declared"
        ],
        None,
        gemini_result.get(
            "manufacturer"
        )
    )

    final["consumer_care"] = reconcile_field(
        paddle_report[
            "consumer_care_declared"
        ],
        None,
        gemini_result.get(
            "consumer_care"
        )
    )

    return final


# # ================================================================
# # 19. FINAL COMPLIANCE EVALUATOR
# # ================================================================

# def evaluate_compliance(
#     final_fields
# ):

#     mandatory_fields = {

#         "mrp":
#             final_fields["mrp"],

#         "net_quantity":
#             final_fields[
#                 "net_quantity"
#             ],

#         "mfg_date":
#             final_fields[
#                 "mfg_date"
#             ],

#         "manufacturer":
#             final_fields[
#                 "manufacturer"
#             ],

#         "consumer_care":
#             final_fields[
#                 "consumer_care"
#             ],
#     }

#     missing = []

#     uncertain = []

#     for field_name, field in (
#         mandatory_fields.items()
#     ):

#         if not field.get(
#             "declared",
#             False
#         ):

#             missing.append(
#                 field_name
#             )

#         elif field.get(
#             "status"
#         ) == "uncertain":

#             uncertain.append(
#                 field_name
#             )

#     # ----------------------------------------------------------
#     # IMPORTANT:
#     #
#     # A disagreement should NOT silently become
#     # COMPLIANT or NON-COMPLIANT.
#     # ----------------------------------------------------------

#     if uncertain:

#         status = "UNCERTAIN"

#     elif missing:

#         status = "NON-COMPLIANT"

#     else:

#         status = "COMPLIANT"

#     return {

#         "overall_status":
#             status,

#         "missing_mandatory_fields":
#             missing,

#         "uncertain_fields":
#             uncertain,
#     }


# ================================================================
# 19. FINAL COMPLIANCE EVALUATOR
# ================================================================

def evaluate_compliance(final_fields):
    mandatory_fields = [
        "mrp",
        "net_quantity",
        "mfg_date",
        "manufacturer",
        "consumer_care",
    ]

    field_status = {}
    uncertain = []
    missing = []

    for field_name in mandatory_fields:
        field = final_fields.get(field_name, {})
        is_declared = field.get("declared", False)
        field_status[field_name] = is_declared

        if not is_declared:
            missing.append(field_name)
        elif field.get("status") == "uncertain":
            uncertain.append(field_name)

    # Compliance logic
    if uncertain:
        verdict = "requires human supervision"
    elif missing:
        verdict = "non-compliant"
    else:
        verdict = "compliant"

    return {
        "field_status": field_status,
        "verdict": verdict,
    }

# ================================================================
# 20. MAIN PIPELINE
# ================================================================

def analyze_package_label(
    image_path,
    use_gemini=True
):

    # ----------------------------------------------------------
    # STEP 1
    # PaddleOCR
    # ----------------------------------------------------------

    boxes = run_ocr_with_boxes(
        image_path
    )

    # ----------------------------------------------------------
    # STEP 2
    # Deterministic geometry extraction
    # ----------------------------------------------------------

    paddle_report = deterministic_extract(
        boxes
    )

    # ----------------------------------------------------------
    # STEP 3
    # Gemini second pass
    # ----------------------------------------------------------

    gemini_response = None

    if use_gemini:

        gemini_response = gemini_validate(
            image_path,
            boxes,
            paddle_report
        )

    # ----------------------------------------------------------
    # STEP 4
    # Reconcile
    # ----------------------------------------------------------

    final_fields = reconcile_results(
        paddle_report,
        gemini_response
    )

    # ----------------------------------------------------------
    # STEP 5
    # Final compliance decision
    # ----------------------------------------------------------

    compliance = evaluate_compliance(
        final_fields
    )

    # ----------------------------------------------------------
    # Final response
    # ----------------------------------------------------------

    return {

        "ocr_boxes":
            boxes,

        "paddleocr_result":
            paddle_report,

        "gemini_validation":
            gemini_response,

        "final_fields":
            final_fields,

        "compliance":
            compliance,
    }


# # ================================================================
# # 21. PRINT REPORT
# # ================================================================

# def print_report(result):

#     print(
#         "\n"
#         + "=" * 70
#     )

#     print(
#         "FINAL LEGAL METROLOGY EXTRACTION"
#     )

#     print(
#         "=" * 70
#     )

#     print(
#         "\nPaddleOCR result:"
#     )

#     print(
#         json.dumps(
#             result[
#                 "paddleocr_result"
#             ],
#             indent=2,
#             ensure_ascii=False
#         )
#     )

#     print(
#         "\nGemini validation:"
#     )

#     print(
#         json.dumps(
#             result[
#                 "gemini_validation"
#             ],
#             indent=2,
#             ensure_ascii=False
#         )
#     )

#     print(
#         "\nFinal fields:"
#     )

#     print(
#         json.dumps(
#             result[
#                 "final_fields"
#             ],
#             indent=2,
#             ensure_ascii=False
#         )
#     )

#     print(
#         "\nCompliance:"
#     )

#     print(
#         json.dumps(
#             result[
#                 "compliance"
#             ],
#             indent=2,
#             ensure_ascii=False
#         )
#     )

#     print(
#         "\n"
#         + "=" * 70
#     )

# ================================================================
# 21. PRINT REPORT
# ================================================================

def print_report(result):
    compliance = result["compliance"]
    
    print("\n--- MANDATORY FIELDS ---")
    for field, is_present in compliance["field_status"].items():
        print(f"{field}: {is_present}")

    print(f"\nFinal Verdict: {compliance['verdict']}\n")


# ================================================================
# 22. ENTRY POINT
# ================================================================

if __name__ == "__main__":

    result = analyze_package_label(
        "/home/vignesh/Projects/package-ocr/test_data/test2.png",
        use_gemini=True
    )

    print_report(result)