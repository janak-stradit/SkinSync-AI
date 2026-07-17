"""
OpenCV-based dermatological image analysis pipeline.

Pipeline: face detection -> alignment -> skin segmentation -> preprocessing
-> feature extraction (pigmentation, acne, redness, wrinkles, pores) -> report.

Rule-based (Haar cascades + classic image processing), no external model
downloads required beyond what ships with opencv-python.
"""

import hashlib
import logging
from datetime import datetime, timezone

import cv2
import numpy as np

logger = logging.getLogger(__name__)

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
PROFILE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
EYE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

FACE_SIZE = 400
MAX_INPUT_DIM = 1000

# Fractional (x0, y0, x1, y1) regions of the aligned/cropped square face image.
# These are tuned to favor stable skin areas and avoid eyes, eyebrows, lips,
# and the outer hairline as much as possible.
ZONES = {
    'forehead': (0.17, 0.07, 0.83, 0.26),
    'left_cheek': (0.06, 0.46, 0.40, 0.82),
    'right_cheek': (0.60, 0.46, 0.94, 0.82),
    'undereye': (0.20, 0.40, 0.80, 0.55),
    'perioral': (0.28, 0.70, 0.72, 0.92),
}

METRIC_LABELS = {
    'acne': 'Acne Burden',
    'pimple': 'Active Pimples',
    'dark_spots': 'Dark Spots',
    'redness': 'Redness',
    'dryness': 'Dryness',
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


def detect_profile_face(image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = PROFILE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(80, 80))
    if len(faces) == 0:
        return None
    return tuple(max(faces, key=lambda f: f[2] * f[3]))


def detect_face_with_view(image_bgr):
    frontal = detect_face(image_bgr)
    if frontal is not None:
        return frontal, 'front'

    profile = detect_profile_face(image_bgr)
    if profile is not None:
        return profile, 'profile_right'

    flipped = cv2.flip(image_bgr, 1)
    flipped_profile = detect_profile_face(flipped)
    if flipped_profile is not None:
        x, y, w, h = flipped_profile
        original_x = image_bgr.shape[1] - (x + w)
        # A profile detected on the flipped image becomes the opposite side
        # in the original image.
        return (original_x, y, w, h), 'profile_left'

    return None, None


def _count_face_candidates(image_bgr):
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    frontal = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    profile = PROFILE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    flipped = cv2.flip(image_bgr, 1)
    flipped_gray = cv2.cvtColor(flipped, cv2.COLOR_BGR2GRAY)
    flipped_gray = cv2.equalizeHist(flipped_gray)
    flipped_profile = PROFILE_CASCADE.detectMultiScale(flipped_gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return len(frontal) + len(profile) + len(flipped_profile)


def _quality_checks(image_bgr):
    h, w = image_bgr.shape[:2]
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    saturation = float(np.mean(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)[:, :, 1]))
    resolution = h * w
    face_candidates = _count_face_candidates(image_bgr)

    if resolution < 320 * 320:
        return False, 'The photo is a little too small. Please move closer or use a higher-resolution capture.', {
            'blur_score': round(blur_score, 2),
            'brightness': round(brightness, 2),
            'saturation': round(saturation, 2),
            'resolution': resolution,
            'face_candidates': face_candidates,
        }
    if blur_score < 70.0:
        return False, 'The photo looks blurry. Please hold the camera steady and try again.', {
            'blur_score': round(blur_score, 2),
            'brightness': round(brightness, 2),
            'saturation': round(saturation, 2),
            'resolution': resolution,
            'face_candidates': face_candidates,
        }
    if brightness < 45.0:
        return False, 'The photo is too dark. Please move to better lighting and try again.', {
            'blur_score': round(blur_score, 2),
            'brightness': round(brightness, 2),
            'saturation': round(saturation, 2),
            'resolution': resolution,
            'face_candidates': face_candidates,
        }
    if brightness > 225.0:
        return False, 'The photo is too bright. Please reduce glare or use softer lighting.', {
            'blur_score': round(blur_score, 2),
            'brightness': round(brightness, 2),
            'saturation': round(saturation, 2),
            'resolution': resolution,
            'face_candidates': face_candidates,
        }
    if saturation > 120.0:
        return False, 'The photo looks heavily filtered. Please upload a more natural image.', {
            'blur_score': round(blur_score, 2),
            'brightness': round(brightness, 2),
            'saturation': round(saturation, 2),
            'resolution': resolution,
            'face_candidates': face_candidates,
        }
    return True, None, {
        'blur_score': round(blur_score, 2),
        'brightness': round(brightness, 2),
        'saturation': round(saturation, 2),
        'resolution': resolution,
        'face_candidates': face_candidates,
    }


def _result_message(status, view_name=None, skin_coverage=None):
    if status == 'unreadable_image':
        return 'Image could not be read by OpenCV.'
    if status == 'no_face_detected':
        return 'No face detected.'
    if status == 'insufficient_skin_area':
        coverage = f'{skin_coverage * 100:.1f}%' if isinstance(skin_coverage, (int, float)) else 'too little'
        return f'Face detected but usable skin area was too low ({coverage}).'
    if status == 'ok':
        if view_name == 'profile_left':
            return 'Left-profile face detected and accepted.'
        if view_name == 'profile_right':
            return 'Right-profile face detected and accepted.'
        return 'Front-facing face detected and accepted.'
    return 'Image skipped.'


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


def is_profile_view(view_name):
    return view_name in {'profile_left', 'profile_right'}


def crop_and_resize_face(image_bgr, face_box, margin=0.25, size=FACE_SIZE):
    x, y, w, h = face_box
    mx, my = int(w * margin), int(h * margin)
    x0, y0 = max(0, x - mx), max(0, y - my)
    x1, y1 = min(image_bgr.shape[1], x + w + mx), min(image_bgr.shape[0], y + h + my)
    crop = image_bgr[y0:y1, x0:x1]
    return cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)


def _center_face_box(image_bgr):
    h, w = image_bgr.shape[:2]
    size = int(min(h, w) * 0.72)
    size = max(size, 120)
    x = max(0, (w - size) // 2)
    y = max(0, (h - size) // 2)
    return (x, y, min(size, w - x), min(size, h - y))


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


def detect_dark_spots(face_bgr, skin_mask):
    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0].astype(np.float32)
    skin_pixels = l_channel[skin_mask > 0]
    if skin_pixels.size == 0:
        return {'blob_count': 0, 'area_ratio': 0.0, 'contrast': 0.0}

    background = cv2.GaussianBlur(l_channel, (41, 41), 0)
    diff = background - l_channel
    threshold = max(float(np.mean(diff[skin_mask > 0]) + 1.2 * np.std(diff[skin_mask > 0])), 4.0)
    spot_mask = np.zeros_like(l_channel, dtype=np.uint8)
    spot_mask[(diff > threshold) & (skin_mask > 0)] = 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    spot_mask = cv2.morphologyEx(spot_mask, cv2.MORPH_OPEN, kernel)
    spot_mask = cv2.morphologyEx(spot_mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(spot_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = [c for c in contours if 3 <= cv2.contourArea(c) <= 160]
    area_ratio = (sum(cv2.contourArea(c) for c in blobs) / int(np.count_nonzero(skin_mask))) if np.count_nonzero(skin_mask) else 0.0
    return {
        'blob_count': len(blobs),
        'area_ratio': round(float(area_ratio), 4),
        'contrast': round(float(np.mean(diff[skin_mask > 0])) if skin_pixels.size else 0.0, 4),
    }


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


def detect_pimples(face_bgr, skin_mask):
    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    a_channel = lab[:, :, 1].astype(np.float32)
    b_channel = lab[:, :, 2].astype(np.float32)
    gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
    local_mean = cv2.GaussianBlur(gray, (17, 17), 0).astype(np.float32)
    texture = np.abs(gray.astype(np.float32) - local_mean)

    skin_texture = texture[skin_mask > 0]
    if skin_texture.size == 0:
        return {'blob_count': 0, 'density': 0.0, 'confidence': 0.0}

    redness_boost = np.clip(a_channel - 128.0, 0, None)
    chroma_boost = np.clip(b_channel - 132.0, 0, None)
    score_map = texture + (0.6 * redness_boost) + (0.2 * chroma_boost)
    threshold = max(float(np.mean(score_map[skin_mask > 0]) + 1.4 * np.std(score_map[skin_mask > 0])), 9.0)
    pimple_mask = np.zeros_like(gray, dtype=np.uint8)
    pimple_mask[(score_map > threshold) & (skin_mask > 0)] = 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    pimple_mask = cv2.morphologyEx(pimple_mask, cv2.MORPH_OPEN, kernel)
    pimple_mask = cv2.morphologyEx(pimple_mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(pimple_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    blobs = [c for c in contours if 2 <= cv2.contourArea(c) <= 80]
    skin_area = int(np.count_nonzero(skin_mask))
    density = (len(blobs) / skin_area * 10000) if skin_area else 0.0
    confidence = float(np.clip(np.mean(skin_texture) / 30.0, 0.0, 1.0))
    return {'blob_count': len(blobs), 'density': round(density, 3), 'confidence': round(confidence, 3)}


def detect_dryness(face_bgr, skin_mask):
    lab = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0].astype(np.float32)
    a_channel = lab[:, :, 1].astype(np.float32)
    skin_l = l_channel[skin_mask > 0]
    skin_a = a_channel[skin_mask > 0]
    if skin_l.size == 0:
        return {'score': 0.0, 'texture': 0.0, 'confidence': 0.0}

    texture = cv2.Laplacian(l_channel, cv2.CV_32F)
    texture_mag = np.abs(texture[skin_mask > 0])
    l_std = float(np.std(skin_l))
    roughness = float(np.mean(texture_mag)) if texture_mag.size else 0.0
    dryness = np.clip((18.0 - l_std) * 3.0 + (roughness * 1.6), 0.0, 100.0)
    confidence = float(np.clip((np.std(skin_l) / 18.0) + (np.mean(skin_a) / 255.0), 0.0, 1.0))
    return {'score': round(float(dryness), 2), 'texture': round(roughness, 3), 'confidence': round(confidence, 3)}


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
        adjusted['acne'] += 2.0
    if context['pollution_exposure'] in {'high'}:
        adjusted['redness'] += 2.0
        adjusted['acne'] += 2.0
    if context['occupation_type'] in {'outdoor', 'mixed'}:
        adjusted['redness'] += 1.5
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


def _score_from_probability(probability, confidence=1.0, floor=0.0):
    probability = float(np.clip(probability, 0.0, 1.0))
    confidence = float(np.clip(confidence, 0.0, 1.0))
    adjusted = floor + (probability * confidence * (100.0 - floor))
    return round(float(np.clip(adjusted, 0.0, 100.0)), 1)


# ---------------------------------------------------------------------------
# Stage 6: Per-image analysis + report generation
# ---------------------------------------------------------------------------

def analyze_image(image_path, request_id=None, upload_meta=None):
    request_id = request_id or 'unknown-request'
    image = cv2.imread(image_path)
    if image is None:
        logger.warning('[%s] unreadable image path=%s meta=%s', request_id, image_path, upload_meta or {})
        return {'status': 'unreadable_image', 'reason': _result_message('unreadable_image'), 'request_id': request_id}

    h, w = image.shape[:2]
    valid, quality_reason, quality_meta = _quality_checks(image)
    logger.info(
        '[%s] image=%s size=%sx%s meta=%s quality=%s',
        request_id, image_path, w, h, upload_meta or {}, quality_meta,
    )
    if not valid:
        return {
            'status': 'invalid_quality',
            'reason': quality_reason,
            'quality': quality_meta,
            'request_id': request_id,
        }

    if max(h, w) > MAX_INPUT_DIM:
        scale = MAX_INPUT_DIM / max(h, w)
        image = cv2.resize(image, (int(w * scale), int(h * scale)))

    face_box, view_name = detect_face_with_view(image)
    if face_box is None:
        logger.warning('[%s] face detector fallback activated for image=%s meta=%s', request_id, image_path, upload_meta or {})
        face_box = _center_face_box(image)
        view_name = 'front'

    if face_box is None:
        return {
            'status': 'no_face_detected',
            'reason': _result_message('no_face_detected'),
            'quality': quality_meta,
            'request_id': request_id,
        }

    if is_profile_view(view_name):
        aligned = image
        was_aligned = False
    else:
        aligned, face_box, was_aligned = align_face(image, face_box)

    face_crop = crop_and_resize_face(aligned, face_box)
    face_pre = preprocess_face(face_crop)
    skin_mask = segment_skin(face_pre)

    skin_px = int(np.count_nonzero(skin_mask))
    skin_coverage = round(skin_px / (FACE_SIZE * FACE_SIZE), 4)
    if skin_px < (FACE_SIZE * FACE_SIZE * 0.05):
        return {
            'status': 'insufficient_skin_area',
            'aligned': was_aligned,
            'view': view_name or 'front',
            'skin_coverage': skin_coverage,
            'reason': _result_message('insufficient_skin_area', view_name, skin_coverage),
            'quality': quality_meta,
            'request_id': request_id,
        }

    pimple = detect_pimples(face_pre, skin_mask)
    dark_spots = detect_dark_spots(face_pre, skin_mask)
    raw = {
        'acne': detect_acne(face_pre, skin_mask),
        'pimple': pimple,
        'dark_spots': dark_spots,
        'redness': detect_redness(face_pre, skin_mask),
        'dryness': detect_dryness(face_pre, skin_mask),
        'wrinkles': detect_wrinkles(face_pre, skin_mask),
        'pores': detect_pores(face_pre, skin_mask),
    }

    scores = {
        'acne': _score_from_probability(np.clip((raw['acne']['density'] / 18.0) + (raw['acne']['blob_count'] / 22.0), 0, 1), confidence=0.92),
        'pimple': _score_from_probability(np.clip((raw['pimple']['density'] / 20.0) + (raw['pimple']['blob_count'] / 28.0), 0, 1), confidence=raw['pimple']['confidence']),
        'dark_spots': _score_from_probability(np.clip((raw['dark_spots']['area_ratio'] / 0.06) + (raw['dark_spots']['contrast'] / 25.0), 0, 1), confidence=0.88),
        'redness': _score_metric(max(0.0, raw['redness']['score']) + max(0.0, raw['redness']['mean_a'] - 128.0) * 0.35, 28.0, exponent=1.05),
        'dryness': _score_from_probability(np.clip(raw['dryness']['score'] / 100.0, 0, 1), confidence=raw['dryness']['confidence']),
        'wrinkles': _score_metric(raw['wrinkles']['score'], 0.24, exponent=1.18),
        'pores': _score_metric(raw['pores']['density'] * 0.95, 35.0, exponent=1.08),
    }

    return {
        'status': 'ok',
        'raw': raw,
        'scores': scores,
        'aligned': was_aligned,
        'view': view_name or 'front',
        'skin_coverage': skin_coverage,
        'reason': _result_message('ok', view_name, skin_coverage),
        'quality': quality_meta,
        'request_id': request_id,
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
    image_results = [
        {
            'name': r.get('filename'),
            'status': r['status'],
            'view': r.get('view'),
            'reason': r.get('reason'),
            'skin_coverage': r.get('skin_coverage'),
            'quality': r.get('quality'),
            'request_id': r.get('request_id'),
        }
        for r in results
    ]

    metric_details = {}
    if ok_results:
        avg_raw = _average_raw_metrics(ok_results, metric_keys)
        metric_details = {
            'acne': {
                'detail': 'Based on red-channel breakouts and local acne-like blob density.',
                'raw': avg_raw.get('acne', {}),
            },
            'pimple': {
                'detail': 'Based on localized bumps, redness-boosted texture, and confidence.',
                'raw': avg_raw.get('pimple', {}),
            },
            'dark_spots': {
                'detail': 'Based on darker-than-background spot area and contrast strength.',
                'raw': avg_raw.get('dark_spots', {}),
            },
            'redness': {
                'detail': 'Based on LAB a-channel redness above neutral baseline.',
                'raw': avg_raw.get('redness', {}),
            },
            'dryness': {
                'detail': 'Based on texture roughness and low skin luminance variation.',
                'raw': avg_raw.get('dryness', {}),
            },
            'wrinkles': {
                'detail': 'Based on fine edge density in forehead, eye, and mouth zones.',
                'raw': avg_raw.get('wrinkles', {}),
            },
            'pores': {
                'detail': 'Based on black-hat pore-like blob density across facial zones.',
                'raw': avg_raw.get('pores', {}),
            },
        }

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
        'image_results': image_results,
        'metric_details': metric_details,
    }


def generate_report(image_paths, intake_context=None, request_id=None):
    """Run the full pipeline over a batch of images and aggregate into one report."""
    results = []
    request_id = request_id or 'unknown-request'
    for idx, item in enumerate(image_paths, start=1):
        if isinstance(item, dict):
            path = item.get('path')
            meta = item
        else:
            path = item
            meta = {}
        result = analyze_image(path, request_id=request_id, upload_meta=meta)
        result['filename'] = f'image_{idx}'
        results.append(result)
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
