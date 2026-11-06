"""Reviewable line proposals for photographs/scans of English handwriting.

Unlike TrOCR, this is LAYOUT processing, not text recognition. All boxes are
heuristic; a reviewer must compare the original. OpenCV is optional so legacy
installations keep working, but the recommended installation includes it.
"""
from __future__ import annotations
from dataclasses import dataclass
from PIL import Image


@dataclass
class Candidate:
    bbox: tuple[int, int, int, int]  # original coordinates for the UI overlay
    image: Image.Image             # optionally deskewed line crop for TrOCR
    angle: float = 0.0


def smart_line_candidates(image: Image.Image, max_lines: int = 80) -> tuple[list[Candidate], dict]:
    """Propose lines by adaptive local contrast, ruling removal and limited deskew.

    Scan at reduced resolution to cap processing cost. Preserve exact original
    page coordinates for manual corrections and image overlays. Do not resize
    the original OCR pixels except for optional page deskew.
    """
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError('Smart line detection needs opencv-python-headless and numpy') from exc
    if image.width < 50 or image.height < 30:
        return [], {'method': 'adaptive_ink', 'reason': 'small_image', 'angle_degrees': 0.}
    rgb = image.convert('RGB')
    w0, h0 = rgb.size
    scale = min(1.0, 1500.0 / w0, 2200.0 / h0)
    w, h = max(1, round(w0 * scale)), max(1, round(h0 * scale))
    thumb = rgb.resize((w, h), Image.Resampling.LANCZOS) if scale < 1 else rgb
    gray = cv2.cvtColor(np.asarray(thumb), cv2.COLOR_RGB2GRAY)
    # Local thresholding handles uneven phone lighting better than a global 185.
    # Median smoothing is intentionally modest to retain small letters and dots.
    gray = cv2.medianBlur(gray, 3)
    block = 41 if min(w, h) >= 55 else 21
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, block, 13)
    # Remove straight, page-wide paper rules and page/table borders. This never
    # substitutes for separating printed questions from handwritten answers.
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                                  cv2.getStructuringElement(cv2.MORPH_RECT, (max(42, round(w * .55)), 1)))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(60, round(h * .55)))))
    ink = cv2.subtract(ink, cv2.bitwise_or(horizontal, vertical))
    # Discard only page margins from the projection, not from the final crop.
    margin = max(3, round(w * .017))
    score_mask = ink.copy()
    score_mask[:, :margin] = 0
    score_mask[:, w-margin:] = 0

    # Projection-based skew estimation on ink: select a rotation only if it
    # improves concentration significantly. +/- 5 degrees is conservative.
    def projected_score(mask):
        rows = np.count_nonzero(mask, axis=1).astype('float64')
        return float(np.sum(rows * rows) / max(1, np.count_nonzero(mask)))
    zero_score = projected_score(score_mask)
    best_angle, best_score = 0., zero_score
    if zero_score > 0 and h >= 90 and w >= 160:
        center = (w / 2, h / 2)
        for a in (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5):
            mat = cv2.getRotationMatrix2D(center, a, 1.0)
            rotated = cv2.warpAffine(score_mask, mat, (w, h),
                                     flags=cv2.INTER_NEAREST, borderValue=0)
            s = projected_score(rotated)
            if s > best_score:
                best_angle, best_score = float(a), s
        if best_angle and best_score >= zero_score * 1.07:
            for a in (best_angle - .5, best_angle + .5):
                if abs(a) > 5.5: continue
                mat = cv2.getRotationMatrix2D(center, a, 1.0)
                rotated = cv2.warpAffine(score_mask, mat, (w, h),
                                         flags=cv2.INTER_NEAREST, borderValue=0)
                s = projected_score(rotated)
                if s > best_score: best_angle, best_score = a, s
        else:
            best_angle = 0.

    if best_angle:
        m = cv2.getRotationMatrix2D((w/2, h/2), best_angle, 1.0)
        ink = cv2.warpAffine(ink, m, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
        full_mat = cv2.getRotationMatrix2D((w0/2, h0/2), best_angle, 1.0)
        deskewed = Image.fromarray(cv2.warpAffine(np.asarray(rgb), full_mat, (w0, h0),
                              flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255)))
        inv = cv2.invertAffineTransform(m)
    else:
        deskewed = rgb
        inv = None

    # A scanned ruled line may be slanted and escape the first morphology
    # pass. Remove any *thin* page-wide residual after deskew as well.
    rules = cv2.morphologyEx(ink, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(40,round(w*.34)), 1)))
    ink = cv2.subtract(ink,rules)
    ink[:, :margin] = 0
    ink[:, w-margin:] = 0
    # Avoid isolated dust specks and sparse scanner noise.
    rows = np.count_nonzero(ink, axis=1)
    min_pixels = max(4, round(w * .006))
    active = np.flatnonzero(rows >= min_pixels)
    if len(active) == 0:
        return [], {'method': 'adaptive_ink', 'reason': 'no_stable_ink', 'angle_degrees': best_angle}
    max_gap = max(3, min(12, round(h * .0045)))
    bands = []
    a = b = int(active[0])
    for y in active[1:]:
        y = int(y)
        if y-b <= max_gap: b = y
        else:
            if b-a >= 3: bands.append((a, b))
            a = b = y
    if b-a >= 3: bands.append((a, b))
    if len(bands) > max_lines:
        raise ValueError('Too many line candidates; manually select question regions')

    candidates = []
    for y0, y1 in bands:
        band = ink[max(0,y0-2):min(h,y1+3), :]
        xx = np.flatnonzero(np.any(band > 0, axis=0))
        if len(xx) == 0: continue
        x0, x1 = int(xx[0]), int(xx[-1])+1
        # Ignore border fragments/small dust; retain short answers like "5".
        if x1-x0 < max(8, round(w*.007)): continue
        # Residual long thin paper rule (do not treat it as a text line).
        if x1-x0 > .82*w and y1-y0 <= max(8, round(h*.018)):
            continue
        px = max(9, round(11*scale)); py = max(5, round(7*scale))
        rect = (max(0,x0-px), max(0,y0-py), min(w,x1+px), min(h,y1+py+1))
        original_crop_box = (max(0,int(rect[0]/scale)),max(0,int(rect[1]/scale)),
                             min(w0,int(round(rect[2]/scale))),min(h0,int(round(rect[3]/scale))))
        if original_crop_box[2]-original_crop_box[0] < 20: continue
        if original_crop_box[3]-original_crop_box[1] < 10: continue
        crop = deskewed.crop(original_crop_box)
        if inv is not None:
            corners = np.asarray([[rect[0],rect[1],1],[rect[2],rect[1],1],
                                  [rect[2],rect[3],1],[rect[0],rect[3],1]], dtype='float64')
            original = corners @ inv.T
            bx0 = max(0, int(np.floor(original[:,0].min()/scale)))
            by0 = max(0, int(np.floor(original[:,1].min()/scale)))
            bx1 = min(w0, int(np.ceil(original[:,0].max()/scale)))
            by1 = min(h0, int(np.ceil(original[:,1].max()/scale)))
            overlay_box = (bx0, by0, bx1, by1)
        else: overlay_box = original_crop_box
        candidates.append(Candidate(overlay_box,crop,round(best_angle,2)))
    return candidates, {'method':'adaptive_ink', 'angle_degrees':round(best_angle,2),
                        'proposed_lines':len(candidates), 'requires_review':True}
