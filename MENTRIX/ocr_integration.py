"""MENTRIX OCR-to-TA local pilot.

Image upload (one question), reviewer-chosen line boundaries, TrOCR inference,
verified transcription, V2 rule engine for supported question types, manual TA
approval and SQLite persistence. Not a student portal or certified grader.
"""
from __future__ import annotations
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import json
import sqlite3
from contextlib import contextmanager

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageOps, UnidentifiedImageError
from adapter import QUESTIONS
from grading_policy import evaluate
from ocr_quality import suggest_boundaries, line_quality, enhanced_line, padded_line

ROOT = Path(__file__).resolve().parent
PRIVATE = ROOT / "local_private_data"
PRIVATE.mkdir(parents=True, exist_ok=True)
DB = PRIVATE / "ocr_reviews.sqlite3"
MAX_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 16_000_000
router = APIRouter(prefix="/api/v1/ocr", tags=["OCR → TA Review"])


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with connection() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS ocr_reviews (
            id TEXT PRIMARY KEY,
            question_id TEXT NOT NULL,
            writer_code TEXT NOT NULL,
            image_filename TEXT NOT NULL,
            image_path TEXT NOT NULL,
            boundaries_json TEXT NOT NULL,
            ocr_prediction TEXT NOT NULL,
            verified_text TEXT,
            transcription_verified INTEGER NOT NULL DEFAULT 0,
            decision TEXT NOT NULL DEFAULT 'needs_review',
            proposed_score REAL,
            decision_reason TEXT NOT NULL,
            final_score REAL,
            reviewer TEXT,
            review_comment TEXT,
            status TEXT NOT NULL DEFAULT 'awaiting_transcription',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        columns={r[1] for r in db.execute('PRAGMA table_info(ocr_reviews)')}
        if 'candidates_json' not in columns:
            db.execute("ALTER TABLE ocr_reviews ADD COLUMN candidates_json TEXT NOT NULL DEFAULT '[]'")
        if 'quality_json' not in columns:
            db.execute("ALTER TABLE ocr_reviews ADD COLUMN quality_json TEXT NOT NULL DEFAULT '[]'")


init_db()


def public_record(row):
    d = dict(row)
    d.pop("image_path", None)
    d.pop("boundaries_json", None)
    for key in ("candidates_json", "quality_json"):
        d[key.removesuffix("_json")] = json.loads(d.pop(key) or "[]")
    d["transcription_verified"] = bool(d["transcription_verified"])
    d["max_score"] = QUESTIONS[d["question_id"]]["max_score"]
    d["question_type"] = QUESTIONS[d["question_id"]]["type"]
    d["image_url"] = f"/api/v1/ocr/reviews/{d['id']}/image"
    return d


def read_review(review_id):
    with connection() as db:
        row = db.execute("SELECT * FROM ocr_reviews WHERE id=?", (review_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "OCR review not found")
    return row


@lru_cache(maxsize=1)
def load_model():
    try:
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    except Exception as e:
        raise RuntimeError("TrOCR dependencies missing. Run INSTALL_OCR_ONCE.bat. Details: " + str(e)) from e
    name = "microsoft/trocr-base-handwritten"
    processor = TrOCRProcessor.from_pretrained(name)
    model = VisionEncoderDecoderModel.from_pretrained(name).to("cpu").eval()
    return torch, processor, model


def run_trocr(lines):
    torch, processor, model = load_model()
    predictions = []
    for img in lines:
        pixels = processor(img.convert("RGB"), return_tensors="pt").pixel_values.to("cpu")
        with torch.inference_mode():
            generated = model.generate(pixels, max_new_tokens=128)
        predictions.append(processor.batch_decode(generated, skip_special_tokens=True)[0])
    return predictions


def validate_boundaries(raw, height):
    try:
        boundaries = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as e:
        raise HTTPException(422, "Boundaries must be a JSON list of image row coordinates") from e
    if (not isinstance(boundaries, list) or len(boundaries) < 2 or len(boundaries) > 41
            or any(type(v) is not int for v in boundaries)):
        raise HTTPException(422, "Supply 2–41 integer line boundaries")
    if boundaries[0] != 0 or boundaries[-1] != height:
        raise HTTPException(422, f"Boundaries must start at 0 and end at image height {height}")
    if any(b <= a or b-a < 8 for a, b in zip(boundaries, boundaries[1:])):
        raise HTTPException(422, "Boundaries must increase, with at least 8 pixels per line")
    return boundaries


@router.get("/config")
def ocr_config():
    return {"mode": "local_only", "model": "microsoft/trocr-base-handwritten",
            "preprocess": "Original RGB (default); optional autocontrast or padded/upscaled candidate comparison", "inference_unit": "human-confirmed line crops",
            "line_suggestion": "projection heuristic; must confirm",
            "essay_grading_model": False, "persists_local_sqlite": True,
            "student_accounts_or_authentication": False, "staff_pin_session_gate": True,
            "question_ids": [{"id": q["question_id"], "prompt": q["prompt"], "type": q["type"],
                              "points": q["max_score"]} for q in QUESTIONS.values()]}


@router.post('/suggest-lines')
async def suggest_lines(image: UploadFile = File(...)):
    """A heuristic for visual aid only: no trained segmentation claim."""
    raw=await image.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES: raise HTTPException(413,'Max 12 MB')
    try:
        with Image.open(BytesIO(raw)) as src:
            if src.format not in ('PNG','JPEG','WEBP') or src.width*src.height>MAX_PIXELS:
                raise HTTPException(422,'Invalid image type or size')
            rgb=ImageOps.exif_transpose(src).convert('RGB')
        return {**suggest_boundaries(rgb),'height':rgb.height,'image_width':rgb.width,
                'verified':False,'warning':'Suggested separators are heuristic, not verified. You MUST inspect each cut.'}
    except (UnidentifiedImageError,OSError,ValueError) as e:
        raise HTTPException(422,'Cannot read image') from e


@router.post("/transcribe", status_code=201)
async def transcribe(image: UploadFile = File(...),
                     question_id: str = Form(...),
                     writer_code: str = Form("ANON"),
                     boundaries: str = Form(...),
                     comparison_mode: str = Form("original")):
    """Do not use external services. Processing is on the user's local CPU."""
    if question_id not in QUESTIONS:
        raise HTTPException(422, "Unknown question ID")
    writer_code = writer_code.strip() or "ANON"
    if len(writer_code) > 36 or not all(c.isascii() and (c.isalnum() or c in "_-.") for c in writer_code):
        raise HTTPException(422, "Writer code must contain only letters, numbers, _, -, .")
    raw = await image.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Max image size is 12 MB")
    if len(raw) < 10:
        raise HTTPException(422, "Empty or invalid image")
    try:
        with Image.open(BytesIO(raw)) as src:
            if src.format not in ("PNG", "JPEG", "WEBP"):
                raise HTTPException(422, "Only PNG, JPEG and WEBP accepted")
            if src.width * src.height > MAX_PIXELS or src.width < 40 or src.height < 20:
                raise HTTPException(422, "Image dimensions are outside allowed range")
            rgb = ImageOps.exif_transpose(src).convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise HTTPException(422, "Cannot read image file") from e
    if comparison_mode not in ('original','compare','padded_compare'):
        raise HTTPException(422,'Unknown OCR comparison mode')
    y = validate_boundaries(boundaries, rgb.height)
    overlap = 12
    lines = [rgb.crop((0, max(0, a-overlap), rgb.width, min(rgb.height, b+overlap)))
             for a, b in zip(y, y[1:])]
    try:
        predictions = run_trocr(lines)
        # Retain the frozen E01 output; generate a separate comparison candidate.
        alternative = run_trocr([enhanced_line(line) for line in lines]) if comparison_mode=='compare' else None
        padded = run_trocr([padded_line(line) for line in lines]) if comparison_mode=='padded_compare' else None
        if len(predictions) != len(lines) or (alternative is not None and len(alternative)!=len(lines)) or (padded is not None and len(padded)!=len(lines)):
            raise RuntimeError('OCR returned a different number of lines')
    except Exception as e:
        raise HTTPException(503, "Local TrOCR could not run: " + str(e)[:450]) from e
    candidates = [{'line':i+1, 'original':original,
                   'autocontrast': alternative[i] if alternative is not None else None,
                   'padded':padded[i] if padded is not None else None}
                  for i,original in enumerate(predictions)]
    quality = [dict(line=i+1, **line_quality(line,predictions[i])) for i,line in enumerate(lines)]
    identifier = str(uuid4())
    local_path = PRIVATE / f"{identifier}.png"
    rgb.save(local_path, format="PNG")
    text = "\n".join(predictions)
    ts = now()
    with connection() as db:
        db.execute("""INSERT INTO ocr_reviews
            (id, question_id, writer_code, image_filename, image_path, boundaries_json,
             ocr_prediction, decision_reason, created_at, updated_at, candidates_json, quality_json)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (identifier, question_id, writer_code, Path(image.filename or "uploaded-image").name[:100],
             str(local_path), json.dumps(y), text,
             "TrOCR output is unverified. Human transcription review required before grading.",
             ts, ts, json.dumps(candidates), json.dumps(quality)))
    return {**public_record(read_review(identifier)), "line_predictions": predictions,
            "model": "microsoft/trocr-base-handwritten", "preprocessing": "Original RGB",
            "comparison_mode":comparison_mode, "line_count": len(lines),
            "warning": "OCR not ground truth. Essay automatic score deliberately unavailable."}


@router.get("/reviews")
def list_reviews():
    with connection() as db:
        rows = db.execute("SELECT * FROM ocr_reviews ORDER BY created_at DESC LIMIT 100").fetchall()
    return {"reviews": [public_record(r) for r in rows]}


@router.get("/reviews/{review_id}")
def review_detail(review_id: str):
    return public_record(read_review(review_id))


@router.get("/reviews/{review_id}/image", include_in_schema=False)
def review_image(review_id: str):
    path = Path(read_review(review_id)["image_path"])
    if not path.is_file() or path.parent != PRIVATE:
        raise HTTPException(404, "Image unavailable")
    return FileResponse(path, media_type="image/png")


class TranscriptionRequest(BaseModel):
    corrected_text: str = Field(min_length=1, max_length=15000)
    verified: bool


@router.post("/reviews/{review_id}/verify")
def verify_transcription(review_id: str, req: TranscriptionRequest):
    if not req.verified:
        raise HTTPException(422, "Reviewer must confirm the transcription matches the original handwriting")
    row = read_review(review_id)
    if row["status"] == "approved":
        raise HTTPException(409, "Already approved; transcription cannot be modified")
    q = QUESTIONS[row["question_id"]]
    # Use the EXACT uploaded rule-based V2 for supported types; essay ALWAYS goes to TA.
    result = evaluate(q, req.corrected_text)
    if q["type"] == "essay_descriptive":
        result = {"decision": "needs_review", "proposed_score": None,
                  "reason": "Essay scoring model not validated: TA must assign score.",
                  "method": "TA_ESSAY_REVIEW"}
    ts = now()
    auto = bool(result.get('auto_scoring_eligible'))
    with connection() as db:
        db.execute("""UPDATE ocr_reviews SET verified_text=?, transcription_verified=1,
                    decision=?, proposed_score=?, decision_reason=?, status=?, final_score=?, reviewer=?, updated_at=?
                    WHERE id=?""",
                   (req.corrected_text, result["decision"], result["proposed_score"],
                    result["reason"], 'auto_scored' if auto else 'pending_ta',
                    result['proposed_score'] if auto else None,
                    'MENTRIX_V2_AUTO_POLICY' if auto else None, ts, review_id))
    return public_record(read_review(review_id))


class ReviewApproval(BaseModel):
    reviewer: str = Field(min_length=2, max_length=80)
    final_score: float = Field(ge=0)
    comment: str = Field(default="", max_length=1000)


@router.post("/reviews/{review_id}/approve")
def approve(review_id: str, req: ReviewApproval):
    row = read_review(review_id)
    if row["status"] == "approved":
        raise HTTPException(409, "Already manually approved")
    if not row["transcription_verified"]:
        raise HTTPException(409, "Verify transcription before approving any grade")
    if req.final_score > QUESTIONS[row["question_id"]]["max_score"]:
        raise HTTPException(422, "Score exceeds maximum")
    with connection() as db:
        db.execute("""UPDATE ocr_reviews SET status='approved', final_score=?,
                   reviewer=?, review_comment=?, updated_at=? WHERE id=?""",
                   (req.final_score, req.reviewer.strip(), req.comment, now(), review_id))
    return public_record(read_review(review_id))
