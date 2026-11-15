import cv2
import numpy as np

MAX_SIDE = 1600  # larger images are shrunk: faster OCR and cheaper Gemini calls


def decode_image(data: bytes) -> np.ndarray | None:
    """Bytes -> BGR image. Transparent areas become white. Returns None if not an image."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if img is None or img.size == 0:
        return None
    if img.dtype != np.uint8:
        img = cv2.convertScaleAbs(img, alpha=1 / 256.0)
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.shape[2] == 4:
        alpha = img[:, :, 3:4].astype(np.float32) / 255.0
        bgr = img[:, :, :3].astype(np.float32)
        return (bgr * alpha + 255.0 * (1.0 - alpha)).astype(np.uint8)
    return img


def downscale(img: np.ndarray, max_side: int = MAX_SIDE) -> np.ndarray:
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1:
        return img
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)


def encode_png(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("Could not encode image")
    return buf.tobytes()