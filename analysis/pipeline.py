"""
OpenCV-based dermatological image analysis pipeline.

Pipeline: face detection -> alignment -> skin segmentation -> preprocessing
-> feature extraction (pigmentation, acne, redness, wrinkles, pores) -> report.

Rule-based (Haar cascades + classic image processing), no external model
downloads required beyond what ships with opencv-python.
"""

import cv2
import numpy as np

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
EYE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

FACE_SIZE = 400
MAX_INPUT_DIM = 1000

# Fractional (x0, y0, x1, y1) regions of the aligned/cropped square face image.
ZONES = {
    'forehead': (0.15, 0.06, 0.85, 0.28),
    'left_cheek': (0.08, 0.50, 0.42, 0.80),
    'right_cheek': (0.58, 0.50, 0.92, 0.80),
    'undereye': (0.18, 0.42, 0.82, 0.55),
    'perioral': (0.25, 0.72, 0.75, 0.92),
}

METRIC_LABELS = {
    'pigmentation': 'Pigmentation',
    'acne': 'Acne / Pimples',
    'redness': 'Redness',
    'wrinkles': 'Fine Lines & Wrinkles',
    'pores': 'Pore Visibility',
}


# ---------------------------------------------------------------------------
# Stage 1: Face Detection
# ---------------------------------------------------------------------------

def detect_face(image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(80, 80))
    if len(faces) == 0:
        return None
    return tuple(max(faces, key=lambda f: f[2] * f[3]))


# ---------------------------------------------------------------------------
# Stage 2: Face Alignment (eye-line rotation)
# ---------------------------------------------------------------------------

def align_face(image_bgr, face_box):
    x, y, w, h = face_box
    roi_gray = cv2.cvtColor(image_bgr[y:y + h, x:x + w], cv2.COLOR_BGR2GRAY)
    eyes = EYE_CASCADE.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=8, minSize=(20, 20))

    if len(eyes) < 2:
        return image_bgr, face_box, False

    eyes = sorted(eyes, key=lambda e: e[0])[:2]
    (ex1, ey1, ew1, eh1), (ex2, ey2, ew2, eh2) = eyes
    left_eye = (x + ex1 + ew1 // 2, y + ey1 + eh1 // 2)
    right_eye = (x + ex2 + ew2 // 2, y + ey2 + eh2 // 2)

    dy = right_eye[1] - left_eye[1]
    dx = right_eye[0] - left_eye[0]
    angle = np.degrees(np.arctan2(dy, dx))

    center = (image_bgr.shape[1] // 2, image_bgr.shape[0] // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image_bgr, rot_mat, (image_bgr.shape[1], image_bgr.shape[0]), flags=cv2.INTER_LINEAR
    )

    realigned_box = detect_face(rotated)
    return rotated, (realigned_box if realigned_box is not None else face_box), True


def crop_and_resize_face(image_bgr, face_box, margin=0.25, size=FACE_SIZE):
    x, y, w, h = face_box
    mx, my = int(w * margin), int(h * margin)
    x0, y0 = max(0, x - mx), max(0, y - my)
    x1, y1 = min(image_bgr.shape[1], x + w + mx), min(image_bgr.shape[0], y + h + my)
    crop = image_bgr[y0:y1, x0:x1]
    return cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)


# ---------------------------------------------------------------------------
# Stage 3: Skin Segmentation (YCrCb thresholding)
# ---------------------------------------------------------------------------

def segment_skin(face_bgr):
    ycrcb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2YCrCb)
    lower = np.array([0, 133, 77], dtype=np.uint8)
    upper = np.array([255, 173, 127], dtype=np.uint8)
    mask = cv2.inRange(ycrcb, lower, upper)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


# ---------------------------------------------------------------------------
# Stage 4: Preprocessing (illumination normalization + denoise)
# ---------------------------------------------------------------------------

def preprocess_face(face_bgr):
    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    normalized = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    return cv2.bilateralFilter(normalized, d=7, sigmaColor=50, sigmaSpace=50)


def _zone_slice(arr, x0f, y0f, x1f, y1f):
    h, w = arr.shape[:2]
    x0, x1 = int(x0f * w), int(x1f * w)
    y0, y1 = int(y0f * h), int(y1f * h)
    return arr[y0:y1, x0:x1]


# ---------------------------------------------------------------------------
# Stage 5: Feature Extraction
# ---------------------------------------------------------------------------

def detect_pigmentation(face_bgr, skin_mask):
    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    skin_pixels = l_channel[skin_mask > 0]
    if skin_pixels.size == 0:
        return {'area_ratio': 0.0, 'blob_count': 0}

    mean_l = float(np.mean(skin_pixels))
    std_l = float(np.std(skin_pixels))
    thresh_val = mean_l - 1.15 * std_l

    dark_mask = np.zeros_like(l_channel, dtype=np.uint8)
    dark_mask[(l_channel < thresh_val) & (skin_mask > 0)] = 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = [c for c in contours if cv2.contourArea(c) >= 4]
    pigmented_area = sum(cv2.contourArea(c) for c in blobs)
    skin_area = int(np.count_nonzero(skin_mask))
    area_ratio = pigmented_area / skin_area if skin_area else 0.0

    return {'area_ratio': round(area_ratio, 4), 'blob_count': len(blobs)}


def detect_acne(face_bgr, skin_mask):
    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    a_channel = lab[:, :, 1].astype(np.float32)
    background = cv2.GaussianBlur(a_channel, (31, 31), 0)
    diff = np.clip(a_channel - background, 0, None)

    skin_diff = diff[skin_mask > 0]
    if skin_diff.size == 0:
        return {'blob_count': 0, 'density': 0.0}

    thresh_val = max(float(np.mean(skin_diff) + 2.0 * np.std(skin_diff)), 6.0)
    spot_mask = np.zeros(a_channel.shape, dtype=np.uint8)
    spot_mask[(diff > thresh_val) & (skin_mask > 0)] = 255

    contours, _ = cv2.findContours(spot_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = [c for c in contours if 2 <= cv2.contourArea(c) <= 120]

    skin_area = int(np.count_nonzero(skin_mask))
    density = (len(blobs) / skin_area * 10000) if skin_area else 0.0
    return {'blob_count': len(blobs), 'density': round(density, 3)}


def detect_redness(face_bgr, skin_mask):
    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    a_channel = lab[:, :, 1]
    skin_a = a_channel[skin_mask > 0]
    if skin_a.size == 0:
        return {'mean_a': 0.0, 'score': 0.0}

    mean_a = float(np.mean(skin_a))
    baseline = 128.0  # neutral a* in OpenCV's 0-255 LAB mapping
    return {'mean_a': round(mean_a, 2), 'score': round(max(0.0, mean_a - baseline), 2)}


def detect_wrinkles(face_bgr, skin_mask):
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    zone_scores = {}
    for name in ('forehead', 'undereye', 'perioral'):
        x0f, y0f, x1f, y1f = ZONES[name]
        zone_gray = _zone_slice(gray, x0f, y0f, x1f, y1f)
        zone_mask = _zone_slice(skin_mask, x0f, y0f, x1f, y1f)
        if zone_gray.size == 0:
            continue

        blurred = cv2.GaussianBlur(zone_gray, (3, 3), 0)
        edges = cv2.Canny(blurred, 25, 70)
        edges = cv2.bitwise_and(edges, edges, mask=zone_mask)

        skin_px = int(np.count_nonzero(zone_mask))
        edge_px = int(np.count_nonzero(edges))
        zone_scores[name] = round((edge_px / skin_px) if skin_px else 0.0, 4)

    avg_score = round(float(np.mean(list(zone_scores.values()))), 4) if zone_scores else 0.0
    return {'zone_scores': zone_scores, 'score': avg_score}


def detect_pores(face_bgr, skin_mask):
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)

    total_count = 0
    total_skin_px = 0
    for name in ('forehead', 'left_cheek', 'right_cheek'):
        x0f, y0f, x1f, y1f = ZONES[name]
        zone_bh = _zone_slice(blackhat, x0f, y0f, x1f, y1f)
        zone_mask = _zone_slice(skin_mask, x0f, y0f, x1f, y1f)
        if zone_bh.size == 0:
            continue

        _, thresh = cv2.threshold(zone_bh, 12, 255, cv2.THRESH_BINARY)
        thresh = cv2.bitwise_and(thresh, thresh, mask=zone_mask)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        blobs = [c for c in contours if 1 <= cv2.contourArea(c) <= 20]
        total_count += len(blobs)
        total_skin_px += int(np.count_nonzero(zone_mask))

    density = (total_count / total_skin_px * 10000) if total_skin_px else 0.0
    return {'blob_count': total_count, 'density': round(density, 3)}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _scale(value, low, high):
    if high <= low:
        return 0.0
    pct = (value - low) / (high - low)
    return float(np.clip(pct, 0.0, 1.0) * 100)


def _severity(score):
    if score < 20:
        return 'minimal'
    if score < 45:
        return 'mild'
    if score < 70:
        return 'moderate'
    return 'severe'


def _normalize_profile_context(intake_context):
    if not intake_context:
        return {}

    skin = intake_context.get('skin_profile') or {}
    lifestyle = intake_context.get('lifestyle_profile') or {}
    diet = intake_context.get('diet_profile') or {}

    def _coerce_list(value):
        if isinstance(value, list):
            return [str(v).strip().lower() for v in value if str(v).strip()]
        if isinstance(value, str):
            return [part.strip().lower() for part in value.split(',') if part.strip()]
        return []

    concerns = _coerce_list(skin.get('skin_concerns'))
    sensitivity = str(skin.get('sensitivity_level') or '').lower()
    acne_level = str(skin.get('acne_level') or '').lower()
    pigmentation_level = str(skin.get('pigmentation_level') or '').lower()
    sunscreen_usage = str(lifestyle.get('sunscreen_usage') or '').lower()
    stress_level = str(lifestyle.get('stress_level') or '').lower()
    screen_time = str(lifestyle.get('screen_time') or '').lower()
    pollution_exposure = str(lifestyle.get('pollution_exposure') or '').lower()
    occupation_type = str(lifestyle.get('occupation_type') or '').lower()
    makeup_usage = str(lifestyle.get('makeup_usage') or '').lower()
    diet_type = str(diet.get('diet_type') or '').lower()

    return {
        'concerns': concerns,
        'sensitivity': sensitivity,
        'acne_level': acne_level,
        'pigmentation_level': pigmentation_level,
        'sunscreen_usage': sunscreen_usage,
        'stress_level': stress_level,
        'screen_time': screen_time,
        'pollution_exposure': pollution_exposure,
        'occupation_type': occupation_type,
        'makeup_usage': makeup_usage,
        'diet_type': diet_type,
    }


def _apply_profile_context(base_scores, intake_context):
    context = _normalize_profile_context(intake_context)
    if not context:
        return base_scores

    adjusted = dict(base_scores)
    concerns = set(context['concerns'])

    if 'acne' in concerns or context['acne_level'] in {'mild', 'moderate', 'severe'}:
        adjusted['acne'] += 6.0
    if 'pigmentation' in concerns or context['pigmentation_level'] in {'mild', 'moderate', 'severe'}:
        adjusted['pigmentation'] += 6.0
    if context['sensitivity'] in {'high', 'sensitive'}:
        adjusted['redness'] += 4.0
        adjusted['acne'] += 2.0
    if context['stress_level'] in {'high'}:
        adjusted['redness'] += 2.0
        adjusted['wrinkles'] += 3.0
    if context['screen_time'] in {'high'}:
        adjusted['wrinkles'] += 2.0
        adjusted['redness'] += 1.0
    if context['sunscreen_usage'] in {'never', 'rarely'}:
        adjusted['pigmentation'] += 2.0
        adjusted['acne'] += 2.0
    if context['pollution_exposure'] in {'high'}:
        adjusted['redness'] += 2.0
        adjusted['acne'] += 2.0
    if context['occupation_type'] in {'outdoor', 'mixed'}:
        adjusted['redness'] += 1.5
        adjusted['pigmentation'] += 1.0
    if context['makeup_usage'] in {'daily_heavy', 'daily_light'}:
        adjusted['pores'] += 2.0
        adjusted['acne'] += 1.0
    if context['diet_type'] in {'non-veg', 'veg', 'vegan'}:
        adjusted['pores'] += 0.5

    return {k: round(float(np.clip(v, 0.0, 100.0)), 1) for k, v in adjusted.items()}


def _score_metric(raw_value, max_value, exponent=1.0):
    if max_value <= 0:
        return 0.0
    normalized = float(np.clip(raw_value / max_value, 0.0, 1.0))
    if exponent != 1.0:
        normalized = float(np.power(normalized, exponent))
    return round(float(np.clip(normalized * 100.0, 0.0, 100.0)), 1)


# ---------------------------------------------------------------------------
# Stage 6: Per-image analysis + report generation
# ---------------------------------------------------------------------------

def analyze_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return {'status': 'unreadable_image'}

    h, w = image.shape[:2]
    if max(h, w) > MAX_INPUT_DIM:
        scale = MAX_INPUT_DIM / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    face_box = detect_face(image)
    if face_box is None:
        return {'status': 'no_face_detected'}

    aligned, face_box, was_aligned = align_face(image, face_box)
    face_crop = crop_and_resize_face(aligned, face_box)
    face_pre = preprocess_face(face_crop)
    skin_mask = segment_skin(face_pre)

    skin_px = int(np.count_nonzero(skin_mask))
    skin_coverage = round(skin_px / (FACE_SIZE * FACE_SIZE), 4)
    if skin_px < (FACE_SIZE * FACE_SIZE * 0.05):
        return {'status': 'insufficient_skin_area', 'aligned': was_aligned, 'skin_coverage': skin_coverage}

    raw = {
        'pigmentation': detect_pigmentation(face_pre, skin_mask),
        'acne': detect_acne(face_pre, skin_mask),
        'redness': detect_redness(face_pre, skin_mask),
        'wrinkles': detect_wrinkles(face_pre, skin_mask),
        'pores': detect_pores(face_pre, skin_mask),
    }

    scores = {
        'pigmentation': _score_metric(raw['pigmentation']['area_ratio'] + raw['pigmentation']['blob_count'] * 0.002, 0.12, exponent=1.15),
        'acne': _score_metric(raw['acne']['density'] + raw['acne']['blob_count'] * 0.6, 25.0, exponent=1.08),
        'redness': _score_metric(max(0.0, raw['redness']['score']) + max(0.0, raw['redness']['mean_a'] - 128.0) * 0.3, 32.0, exponent=1.05),
        'wrinkles': _score_metric(raw['wrinkles']['score'], 0.25, exponent=1.2),
        'pores': _score_metric(raw['pores']['density'] * 0.95, 40.0, exponent=1.1),
    }

    return {
        'status': 'ok',
        'raw': raw,
        'scores': scores,
        'aligned': was_aligned,
        'skin_coverage': skin_coverage,
    }


STAGE_LABELS = {
    'face_detection': 'Face Detection',
    'alignment': 'Face Alignment',
    'segmentation': 'Skin Segmentation',
    'preprocessing': 'Preprocessing',
    'feature_extraction': 'Feature Extraction',
    'scoring': 'Scoring',
}


def _average_raw_metrics(ok_results, metric_keys):
    raw_avg = {}
    for m in metric_keys:
        dicts = [r['raw'][m] for r in ok_results]
        avg = {}
        for k in dicts[0].keys():
            vals = [d[k] for d in dicts if isinstance(d.get(k), (int, float))]
            if vals:
                avg[k] = round(float(np.mean(vals)), 4)
        raw_avg[m] = avg
    return raw_avg


def _build_stage_details(results, ok_results, metric_keys):
    total = len(results)
    status_counts = {}
    for r in results:
        status_counts[r['status']] = status_counts.get(r['status'], 0) + 1

    unreadable = status_counts.get('unreadable_image', 0)
    no_face = status_counts.get('no_face_detected', 0)
    insufficient_skin = status_counts.get('insufficient_skin_area', 0)
    images_with_face = total - unreadable - no_face

    coverage_results = [r for r in results if 'skin_coverage' in r]
    avg_coverage_pct = (
        round(float(np.mean([r['skin_coverage'] for r in coverage_results])) * 100, 1)
        if coverage_results else None
    )
    aligned_count = sum(1 for r in coverage_results if r.get('aligned'))

    return {
        'face_detection': {
            'label': STAGE_LABELS['face_detection'],
            'images_total': total,
            'images_with_face': images_with_face,
            'images_failed': unreadable + no_face,
        },
        'alignment': {
            'label': STAGE_LABELS['alignment'],
            'images_processed': len(coverage_results),
            'images_aligned': aligned_count,
        },
        'segmentation': {
            'label': STAGE_LABELS['segmentation'],
            'avg_skin_coverage_pct': avg_coverage_pct,
            'images_insufficient_skin': insufficient_skin,
        },
        'preprocessing': {
            'label': STAGE_LABELS['preprocessing'],
            'images_processed': len(ok_results),
            'techniques': ['CLAHE illumination normalization', 'Bilateral denoising'],
        },
        'feature_extraction': {
            'label': STAGE_LABELS['feature_extraction'],
            'images_analyzed': len(ok_results),
            'raw': _average_raw_metrics(ok_results, metric_keys) if ok_results else {},
        },
        'scoring': {
            'label': STAGE_LABELS['scoring'],
            'images_used': len(ok_results),
        },
    }


def generate_report(image_paths, intake_context=None):
    """Run the full pipeline over a batch of images and aggregate into one report."""
    results = [analyze_image(p) for p in image_paths]
    ok_results = [r for r in results if r['status'] == 'ok']
    metric_keys = list(METRIC_LABELS.keys())
    stage_details = _build_stage_details(results, ok_results, metric_keys)

    if not ok_results:
        return {
            'status': 'failed',
            'images_analyzed': 0,
            'images_skipped': len(results),
            'overall_skin_health_score': None,
            'metrics': None,
            'stage_details': stage_details,
            'message': (
                'No usable face could be detected in the uploaded images. '
                'Please upload clear, well-lit, front-facing photos.'
            ),
        }

    if len(ok_results) < 3:
        return {
            'status': 'failed',
            'images_analyzed': len(ok_results),
            'images_skipped': len(results) - len(ok_results),
            'overall_skin_health_score': None,
            'metrics': None,
            'stage_details': stage_details,
            'message': (
                f'At least 3 usable face images are required for a reliable analysis. '
                f'Only {len(ok_results)} usable image(s) were detected.'
            ),
        }

    avg_scores = {
        m: round(float(np.mean([r['scores'][m] for r in ok_results])), 1)
        for m in metric_keys
    }
    adjusted_scores = _apply_profile_context(avg_scores, intake_context)
    overall_health_score = round(100 - float(np.mean(list(adjusted_scores.values()))), 1)

    metrics = {
        m: {
            'label': METRIC_LABELS[m],
            'score': adjusted_scores[m],
            'severity': _severity(adjusted_scores[m]),
        }
        for m in metric_keys
    }

    return {
        'status': 'ok',
        'images_analyzed': len(ok_results),
        'images_skipped': len(results) - len(ok_results),
        'overall_skin_health_score': overall_health_score,
        'metrics': metrics,
        'stage_details': stage_details,
        'message': None,
    }
