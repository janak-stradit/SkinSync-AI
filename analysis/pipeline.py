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
        return image_bgr, face_box

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
    return rotated, (realigned_box if realigned_box is not None else face_box)


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

    aligned, face_box = align_face(image, face_box)
    face_crop = crop_and_resize_face(aligned, face_box)
    face_pre = preprocess_face(face_crop)
    skin_mask = segment_skin(face_pre)

    skin_px = int(np.count_nonzero(skin_mask))
    if skin_px < (FACE_SIZE * FACE_SIZE * 0.05):
        return {'status': 'insufficient_skin_area'}

    raw = {
        'pigmentation': detect_pigmentation(face_pre, skin_mask),
        'acne': detect_acne(face_pre, skin_mask),
        'redness': detect_redness(face_pre, skin_mask),
        'wrinkles': detect_wrinkles(face_pre, skin_mask),
        'pores': detect_pores(face_pre, skin_mask),
    }

    scores = {
        'pigmentation': round(_scale(raw['pigmentation']['area_ratio'], 0.0, 0.12), 1),
        'acne': round(_scale(raw['acne']['density'], 0.0, 25.0), 1),
        'redness': round(_scale(raw['redness']['score'], 0.0, 32.0), 1),
        'wrinkles': round(_scale(raw['wrinkles']['score'], 0.0, 0.25), 1),
        'pores': round(_scale(raw['pores']['density'], 0.0, 40.0), 1),
    }

    return {'status': 'ok', 'raw': raw, 'scores': scores}


def generate_report(image_paths):
    """Run the full pipeline over a batch of images and aggregate into one report."""
    results = [analyze_image(p) for p in image_paths]
    ok_results = [r for r in results if r['status'] == 'ok']

    if not ok_results:
        return {
            'status': 'failed',
            'images_analyzed': 0,
            'images_skipped': len(results),
            'overall_skin_health_score': None,
            'metrics': None,
            'message': (
                'No usable face could be detected in the uploaded images. '
                'Please upload clear, well-lit, front-facing photos.'
            ),
        }

    metric_keys = list(METRIC_LABELS.keys())
    avg_scores = {
        m: round(float(np.mean([r['scores'][m] for r in ok_results])), 1)
        for m in metric_keys
    }
    overall_health_score = round(100 - float(np.mean(list(avg_scores.values()))), 1)

    metrics = {
        m: {
            'label': METRIC_LABELS[m],
            'score': avg_scores[m],
            'severity': _severity(avg_scores[m]),
        }
        for m in metric_keys
    }

    return {
        'status': 'ok',
        'images_analyzed': len(ok_results),
        'images_skipped': len(results) - len(ok_results),
        'overall_skin_health_score': overall_health_score,
        'metrics': metrics,
        'message': None,
    }
