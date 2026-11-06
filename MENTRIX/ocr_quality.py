"""Local OCR assistance for the human-in-the-loop pilot.

Suggestions and warning heuristics are NOT trained models, accuracy estimates or
valid replacements for comparing predictions with handwritten ground truth.
"""
from __future__ import annotations
from collections import Counter
from PIL import Image, ImageOps, ImageFilter, ImageStat
import re


def enhanced_line(image: Image.Image) -> Image.Image:
    """Second, manually selectable candidate; not asserted superior to E01 RGB."""
    rgb = image.convert('RGB')
    # Gently increase contrast WITHOUT hard thresholding (E05 hurt in pilot).
    return ImageOps.autocontrast(rgb, cutoff=1, preserve_tone=False)


def padded_line(image: Image.Image) -> Image.Image:
    """Optional reversible candidate: border padding + limited upscaling for small line crops.
    Not a claimed accuracy improvement; users compare with original prediction.
    """
    rgb=image.convert('RGB')
    if rgb.height < 72 and rgb.width < 1400:
        rgb=rgb.resize((rgb.width*2,rgb.height*2),Image.Resampling.BICUBIC)
    return ImageOps.expand(rgb, border=(18,15,18,15), fill=(255,255,255))


def line_quality(img: Image.Image, prediction: str = '') -> dict:
    g = ImageOps.grayscale(img)
    stats = ImageStat.Stat(g)
    contrast = stats.stddev[0]
    histogram = g.histogram()
    pixels = max(1, img.width * img.height)
    dark = sum(histogram[:135]) / pixels
    flags = []
    if contrast < 17 or dark < 0.003:
        flags.append('Low visible ink/contrast: inspect this crop; it may be blank or faint.')
    if img.width / max(1, img.height) < 1.0:
        flags.append('Very tall line crop: line segmentation may include multiple lines.')
    if img.height < 24:
        flags.append('Very short crop: characters may be clipped.')
    s = prediction.strip()
    if s and len(re.findall(r'[A-Za-z]', s)) < 2:
        flags.append('OCR contains almost no readable letters.')
    words = re.findall(r'\b[a-z]{2,}\b', s.lower())
    if len(words) >= 6 and Counter(words).most_common(1)[0][1] >= 4:
        flags.append('OCR repeats a word unusually often; human verification required.')
    return {'contrast_std': round(contrast, 1), 'dark_pixel_fraction': round(dark, 4), 'flags': flags}


def suggest_boundaries(image: Image.Image) -> dict:
    """Conservative projection-heuristic; reviewer MUST inspect/edit every cut.
    Failure to find reliable gaps yields [0,height], not invented line splitting.
    """
    image = ImageOps.exif_transpose(image).convert('RGB')
    w, h = image.size
    if h < 55 or w < 50:
        return {'boundaries': [0, h], 'message': 'Image too small to suggest dividers.'}
    # Resize to fixed width to avoid per-pixel work on very large phone photos.
    scale = min(1., 650/w)
    g = ImageOps.grayscale(image)
    if scale < 1:
        g = g.resize((max(1, round(w*scale)), max(1, round(h*scale))), Image.Resampling.BILINEAR)
    g = ImageOps.autocontrast(g, cutoff=2).filter(ImageFilter.MedianFilter(size=3))
    ww, hh = g.size
    pix = g.load()
    # In pages with dark shadows Otsu may select too much; threshold below 160.
    hist = g.histogram()
    total = ww*hh
    s_all = sum(v*i for i,v in enumerate(hist)); sum_b=0; w_b=0; best=-1; otsu=135
    for i,v in enumerate(hist):
        w_b += v
        if not w_b: continue
        w_f = total-w_b
        if not w_f: break
        sum_b += i*v
        mu_b = sum_b/w_b; mu_f=(s_all-sum_b)/w_f
        score = w_b*w_f*(mu_b-mu_f)**2
        if score>best: best=score; otsu=i
    threshold = max(65, min(163, otsu))
    counts = []
    for y in range(hh):
        counts.append(sum(pix[x,y] < threshold for x in range(ww)))
    # Ignore scattered single-pixel noise; medium horizontal ink density.
    min_ink=max(3,round(ww*.012))
    active = [i for i,n in enumerate(counts) if n >= min_ink]
    if not active: return {'boundaries':[0,h], 'message':'No stable ink bands found. Mark line dividers manually.'}
    gap_max=max(4, round(hh*.012))
    clusters=[]; start=last=active[0]
    for y in active[1:]:
        if y-last <= gap_max: last=y
        else:
            if last-start >= max(4, round(hh*.006)): clusters.append((start,last))
            start=last=y
    if last-start >= max(4,round(hh*.006)):clusters.append((start,last))
    if len(clusters)<2:
        return {'boundaries':[0,h], 'message':'Could not find reliable gaps. Add dividers manually.'}
    # Limit suspicious many short bands to avoid false automatic boundaries.
    if len(clusters)>40:
        return {'boundaries':[0,h], 'message':'Too many possible text bands: manual division is safer.'}
    cuts = [0]
    for (a,b),(c,d) in zip(clusters,clusters[1:]):
        gap=(b+c)//2
        y=round(gap*h/hh)
        if y-cuts[-1] >= 10 and y <= h-10: cuts.append(y)
    cuts.append(h)
    if any(b-a < 8 for a,b in zip(cuts,cuts[1:])) or len(cuts)>41:
        cuts=[0,h]
    return {'boundaries':cuts, 'message':f'Suggested {len(cuts)-1} bands. Inspect every red boundary; these are NOT verified line cuts.', 'threshold':threshold}
