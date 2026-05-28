"""
Node A: Quality Gatekeeper.

Objective of this node:
Filter candidate images suitable for the subsequent visual annotation stage from Dataset v0 images.

According to project documents and course requirements, Node A needs to complete:

1. Read Dataset v0 images
2. Keep full-body/half-body Outfit images
3. Remove text screenshots, landscape images, and marketing duplicates
4. Output quality_filtered_images.csv
5. Output a log file recording the number and types of filtered items

Current version notes:
This script currently implements a "local rule-based" quality gatekeeper and does not rely on external APIs.
It can stably complete the following filtering:

- File does not exist
- Image is corrupted
- Image size is too small
- Abnormal image aspect ratio
- Suspected duplicate images

For finer classification such as "full-body/half-body Outfit, text screenshot, landscape, product marketing", 
local rules cannot judge very reliably, so currently all images that pass the basic quality screening are uniformly
marked as candidate_outfit.

VLM judgment logic can be added in this script later, for example:
    classify_image_with_vlm(image_path)

To let Qwen-VL-Max output:
    full_body_outfit / half_body_outfit / text_screenshot / landscape / product_marketing

This will further meet the requirements for more refined quality gatekeeping.
"""

import csv
import colorsys
import json
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, UnidentifiedImageError

from config import (
    DUPLICATE_HASH_DISTANCE,
    ENABLE_YOLO_LANDSCAPE_FILTER,
    HASH_SIZE,
    IMAGE_TYPE_BAD_RATIO,
    IMAGE_TYPE_CORRUPTED,
    IMAGE_TYPE_DUPLICATE,
    IMAGE_TYPE_LANDSCAPE,
    IMAGE_TYPE_MISSING,
    IMAGE_TYPE_TOO_SMALL,
    IMAGE_TYPE_VALID,
    LANDSCAPE_ANALYSIS_SIZE,
    LANDSCAPE_BLUE_RATIO_THRESHOLD,
    LANDSCAPE_FOREGROUND_COMPONENT_THRESHOLD,
    LANDSCAPE_GREEN_RATIO_THRESHOLD,
    LANDSCAPE_MIXED_BLUE_RATIO_THRESHOLD,
    LANDSCAPE_MIXED_GREEN_RATIO_THRESHOLD,
    LANDSCAPE_NATURE_RATIO_THRESHOLD,
    LANDSCAPE_NO_PERSON_NATURE_RATIO_THRESHOLD,
    LANDSCAPE_PERSON_KEEP_RATIO_THRESHOLD,
    LANDSCAPE_SMALL_PERSON_NATURE_RATIO_THRESHOLD,
    LANDSCAPE_SMALL_PERSON_RATIO_THRESHOLD,
    LANDSCAPE_TOTAL_PERSON_KEEP_RATIO_THRESHOLD,
    LANDSCAPE_GROUP_PERSON_COUNT_KEEP_THRESHOLD,
    MAX_ASPECT_RATIO,
    MIN_ASPECT_RATIO,
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_WIDTH,
    QUALITY_FILTER_LOG_JSON,
    QUALITY_FILTERED_CSV,
    YOLO_MODEL_PATH,
    YOLO_PERSON_CONFIDENCE_THRESHOLD,
    ensure_output_dirs,
)

from data_loader import load_image_records


YOLO_PERSON_CLASS_ID = 0
_YOLO_MODEL = None


def compute_average_hash(image: Image.Image, hash_size: int=HASH_SIZE) -> str:
    """
    Calculate the average hash of the image.

    Average hash is a simple perceptual hashing method:
    1. Resize the image to hash_size x hash_size
    2. Convert to grayscale image
    3. Calculate the average value of all pixels
    4. Mark each pixel greater than or equal to the average as 1, otherwise 0
    5. Finally, obtain a 0/1 string

    If two images are visually very similar, their hashes are usually very close.
    Therefore, it can be used for "suspected duplicate image" filtering.

    Args:
        image:
            PIL Image object.
        hash_size:
            Hash size, default is from config.py.

    Returns:
        str:
            A hash string consisting of 0s and 1s, e.g., length 64.
    """
    gray_image = image.convert("L").resize((hash_size, hash_size)) # Convert to grayscale and resize
    pixels = list(gray_image.getdata()) # Get pixel value list
    avg_pixel = sum(pixels) / len(pixels) # Calculate average pixel value

    bits = ["1" if pixel >= avg_pixel else "0" for pixel in pixels] # Generate 0/1 string based on average
    return "".join(bits)

def hamming_distance(hash_a: str, hash_b: str) -> int:
    """
    Calculate the Hamming distance between two hash strings.

    Hamming distance represents the number of different characters at the same position of two strings.
    For image hashes, a smaller distance means the images are more similar.

    Args:
        hash_a:
            The first hash string.
        hash_b:
            The second hash string.

    Returns:
        int:
            Hamming distance.
    """
    if len(hash_a) != len(hash_b):
        raise ValueError("Inconsistent hash lengths, cannot calculate Hamming distance.")

    return sum(char_a != char_b for char_a, char_b in zip(hash_a, hash_b))

def find_duplicate_hash(
    current_hash: str,
    existing_hashes: Dict[str, str],
    threshold: int = DUPLICATE_HASH_DISTANCE,
) -> Optional[str]:
    """
    Check whether the current image is a suspected duplicate of existing images.

    Args:
        current_hash:
            Average hash of the current image.
        existing_hashes:
            A dictionary of image hashes that have passed screening.
            key is Image_ID, value is image hash.
        threshold:
            Hamming distance threshold.
            When less than or equal to this value, the current image is considered a duplicate.

    Returns:
        Optional[str]:
            If a duplicate is found, return the duplicated existing Image_ID.
            If no duplicate, return None.
    """
    for existing_image_id, existing_hash in existing_hashes.items():
        distance = hamming_distance(current_hash, existing_hash)

        if distance <= threshold:
            return existing_image_id

    return None


def analyze_nature_color_distribution(
    image: Image.Image,
    analysis_size: int = LANDSCAPE_ANALYSIS_SIZE,
) -> Tuple[float, float, float, float]:
    """
    Estimate the proportion of natural green and sky/water blue in the image.

    This function refers to the HSV color parsing idea in draft.py, but uses PIL + colorsys
    to avoid adding extra dependencies like OpenCV / YOLO to Node A.

    Returns:
        Tuple[float, float, float, float]:
            nature_ratio, green_ratio, blue_ratio, foreground_component_ratio
    """
    rgb_image = image.convert("RGB").resize((analysis_size, analysis_size))
    pixels = list(rgb_image.getdata())

    green_pixels = 0
    blue_pixels = 0
    saturated_non_nature_mask: List[bool] = []

    for red, green, blue in pixels:
        hue, saturation, value = colorsys.rgb_to_hsv(
            red / 255,
            green / 255,
            blue / 255,
        )

        # Align with common OpenCV HSV ranges: H 0-179, S/V 0-255.
        hue = hue * 179
        saturation = saturation * 255
        value = value * 255

        is_green = 35 <= hue <= 85 and saturation >= 40 and value >= 40
        is_blue = 90 <= hue <= 130 and saturation >= 40 and value >= 40

        if is_green:
            green_pixels += 1
        elif is_blue:
            blue_pixels += 1

        # Red/black/high saturation clothing or gear can easily form foreground subjects.
        # If such areas form large blocks, even if natural colors are high, it's more like outdoor outfit/activity photos.
        saturated_non_nature_mask.append(
            saturation >= 50 and value >= 35 and not is_green and not is_blue
        )

    total_pixels = len(pixels)
    green_ratio = green_pixels / total_pixels
    blue_ratio = blue_pixels / total_pixels
    nature_ratio = green_ratio + blue_ratio
    foreground_component_ratio = find_largest_component_ratio(
        saturated_non_nature_mask,
        width=analysis_size,
        height=analysis_size,
    )

    return nature_ratio, green_ratio, blue_ratio, foreground_component_ratio


def find_largest_component_ratio(mask: List[bool], width: int, height: int) -> float:
    """
    Calculate the ratio of the largest four-connected component in the binary mask to the whole image.
    """
    seen = [False] * len(mask)
    largest_component = 0

    for start_index, is_active in enumerate(mask):
        if not is_active or seen[start_index]:
            continue

        stack = [start_index]
        seen[start_index] = True
        component_size = 0

        while stack:
            current = stack.pop()
            component_size += 1
            x = current % width
            y = current // width

            for neighbor_x, neighbor_y in (
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1),
            ):
                if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                    continue

                neighbor_index = neighbor_y * width + neighbor_x
                if mask[neighbor_index] and not seen[neighbor_index]:
                    seen[neighbor_index] = True
                    stack.append(neighbor_index)

        largest_component = max(largest_component, component_size)

    return largest_component / len(mask)


def get_yolo_model():
    """
    Lazy load YOLOv8n model.

    Import ultralytics only when YOLO landscape filter is enabled, to avoid Node A 
    failing on startup in environments without optional dependencies.
    """
    global _YOLO_MODEL

    if _YOLO_MODEL is not None:
        return _YOLO_MODEL

    if not YOLO_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find YOLO weights file: {YOLO_MODEL_PATH}. "
            "Please download yolov8n.pt first, or disable ENABLE_YOLO_LANDSCAPE_FILTER in config.py."
        )

    try:
        from ultralytics import YOLO
    except ImportError as e:
        raise ImportError(
            "ultralytics is not installed, cannot enable YOLO landscape filtering. "
            "Please install ultralytics in the current Python environment, or disable ENABLE_YOLO_LANDSCAPE_FILTER."
        ) from e

    _YOLO_MODEL = YOLO(str(YOLO_MODEL_PATH))
    return _YOLO_MODEL


def analyze_person_subject_area(image_path: Path, image_area: int) -> Dict[str, float]:
    """
    Use YOLOv8n to detect person and calculate the person subject area ratio.

    Returns:
        Dict[str, float]:
            person_count, total_person_ratio, max_person_ratio, max_person_confidence
    """
    if not ENABLE_YOLO_LANDSCAPE_FILTER:
        return {
            "person_count": -1,
            "total_person_ratio": -1.0,
            "max_person_ratio": -1.0,
            "max_person_confidence": -1.0,
        }

    model = get_yolo_model()
    prediction = model.predict(
        source=str(image_path),
        conf=YOLO_PERSON_CONFIDENCE_THRESHOLD,
        classes=[YOLO_PERSON_CLASS_ID],
        verbose=False,
    )[0]

    person_count = 0
    total_person_area = 0.0
    max_person_area = 0.0
    max_person_confidence = 0.0

    for box in prediction.boxes:
        confidence = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        box_area = max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))

        person_count += 1
        total_person_area += box_area
        max_person_area = max(max_person_area, box_area)
        max_person_confidence = max(max_person_confidence, confidence)

    return {
        "person_count": person_count,
        "total_person_ratio": min(total_person_area / image_area, 1.0),
        "max_person_ratio": min(max_person_area / image_area, 1.0),
        "max_person_confidence": max_person_confidence,
    }


def is_high_confidence_landscape(
    image: Image.Image,
    image_path: Path,
) -> Tuple[bool, str, float]:
    """
    Determine if the image is a high-confidence pure landscape/empty scene candidate.

    Filter two types of high-confidence landscape/empty scenes here:
    - Large areas of blue sky/water/snow mountain
    - Large areas of green grass/forest
    - Person subject is missing or very small, cannot be an outfit analysis target

    We do not use the single rule of "filter if no person detected" from draft.py, because the current dataset
    includes product flat-lays, local close-ups, text-image pages, and outfit illustrations, which need to be judged alongside natural colors.
    """
    (
        nature_ratio,
        green_ratio,
        blue_ratio,
        foreground_component_ratio,
    ) = analyze_nature_color_distribution(image)

    metric_text = (
        f"nature={nature_ratio:.3f}, green={green_ratio:.3f}, "
        f"blue={blue_ratio:.3f}, foreground={foreground_component_ratio:.3f}"
    )

    person_metrics = analyze_person_subject_area(
        image_path=image_path,
        image_area=image.width * image.height,
    )

    person_count = int(person_metrics["person_count"])
    total_person_ratio = person_metrics["total_person_ratio"]
    max_person_ratio = person_metrics["max_person_ratio"]
    person_text = (
        f"persons={person_count}, total_person={person_metrics['total_person_ratio']:.3f}, "
        f"max_person={max_person_ratio:.3f}, max_conf={person_metrics['max_person_confidence']:.3f}"
    )
    full_metric_text = f"{metric_text}, {person_text}"

    if max_person_ratio >= LANDSCAPE_PERSON_KEEP_RATIO_THRESHOLD:
        return (
            False,
            f"not_landscape_person_subject_large_enough: {full_metric_text}",
            nature_ratio,
        )

    if (
        person_count >= LANDSCAPE_GROUP_PERSON_COUNT_KEEP_THRESHOLD
        or total_person_ratio >= LANDSCAPE_TOTAL_PERSON_KEEP_RATIO_THRESHOLD
    ):
        return (
            False,
            f"not_landscape_people_present_as_scene_subject: {full_metric_text}",
            nature_ratio,
        )

    if foreground_component_ratio >= LANDSCAPE_FOREGROUND_COMPONENT_THRESHOLD:
        return (
            False,
            f"not_landscape_has_large_foreground_subject: {full_metric_text}",
            nature_ratio,
        )

    if (
        person_count == 0
        and nature_ratio >= LANDSCAPE_NO_PERSON_NATURE_RATIO_THRESHOLD
    ):
        return (
            True,
            f"landscape_no_person_nature_dominant: {full_metric_text}",
            nature_ratio,
        )

    if (
        person_count > 0
        and max_person_ratio < LANDSCAPE_SMALL_PERSON_RATIO_THRESHOLD
        and nature_ratio >= LANDSCAPE_SMALL_PERSON_NATURE_RATIO_THRESHOLD
    ):
        return (
            True,
            f"landscape_person_too_small_nature_dominant: {full_metric_text}",
            nature_ratio,
        )

    if nature_ratio < LANDSCAPE_NATURE_RATIO_THRESHOLD:
        return (
            False,
            f"not_landscape_by_color_and_subject: {full_metric_text}",
            nature_ratio,
        )

    has_dominant_blue = blue_ratio >= LANDSCAPE_BLUE_RATIO_THRESHOLD
    has_dominant_green = green_ratio >= LANDSCAPE_GREEN_RATIO_THRESHOLD
    has_mixed_nature = (
        green_ratio >= LANDSCAPE_MIXED_GREEN_RATIO_THRESHOLD
        and blue_ratio >= LANDSCAPE_MIXED_BLUE_RATIO_THRESHOLD
    )

    if has_dominant_blue or has_dominant_green or has_mixed_nature:
        return (
            True,
            f"high_confidence_landscape_by_nature_color: {full_metric_text}",
            nature_ratio,
        )

    return (
        False,
        f"not_landscape_by_color_mix: {full_metric_text}",
        nature_ratio,
    )


def inspect_basic_image_quality(
    image_path: Path,
) -> Tuple[bool, str, Optional[str], Optional[int], Optional[int], Optional[float], Optional[str]]:
    """
    Inspect basic image quality.

    This function only performs "highly certain" basic checks:
    - Whether the file exists
    - Whether the image can be opened by PIL
    - Whether the image width/height is sufficient
    - Whether the image aspect ratio is within a reasonable range

    Args:
        image_path:
            Absolute path of the image.

    Returns:
        Tuple:
            passed:
                Whether it passed the basic quality check.
            image_type:
                Image type label.
            reject_reason:
                Reason for rejection if failed; None if passed.
            width:
                Image width.
            height:
                Image height.
            aspect_ratio:
                Image aspect ratio.
            image_hash:
                Image average hash; None if the image cannot be opened.
    """
    if not image_path.exists():
        return (
            False,
            IMAGE_TYPE_MISSING,
            "image_file_not_found",
            None,
            None,
            None,
            None,
        )

    try:
        with Image.open(image_path) as img:
            # load() will forcibly read the image data.
            # Some corrupted images might not throw an error during the open stage, but will throw an error during the load stage.
            img.load()

            width, height = img.size

            if width <= 0 or height <= 0:
                return (
                    False,
                    IMAGE_TYPE_CORRUPTED,
                    "invalid_image_size",
                    width,
                    height,
                    None,
                    None,
                )

            aspect_ratio = width / height

            if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
                return (
                    False,
                    IMAGE_TYPE_TOO_SMALL,
                    "image_too_small",
                    width,
                    height,
                    aspect_ratio,
                    None,
                )

            if aspect_ratio > MAX_ASPECT_RATIO or aspect_ratio < MIN_ASPECT_RATIO:
                return (
                    False,
                    IMAGE_TYPE_BAD_RATIO,
                    "abnormal_aspect_ratio",
                    width,
                    height,
                    aspect_ratio,
                    None,
                )

            is_landscape, landscape_reason, _ = is_high_confidence_landscape(
                image=img,
                image_path=image_path,
            )

            if is_landscape:
                return (
                    False,
                    IMAGE_TYPE_LANDSCAPE,
                    landscape_reason,
                    width,
                    height,
                    aspect_ratio,
                    None,
                )

            image_hash = compute_average_hash(img)

            return (
                True,
                IMAGE_TYPE_VALID,
                None,
                width,
                height,
                aspect_ratio,
                image_hash,
            )

    except (UnidentifiedImageError, OSError, ValueError) as e:
        return (
            False,
            IMAGE_TYPE_CORRUPTED,
            f"cannot_open_image: {str(e)}",
            None,
            None,
            None,
            None,
        )
    
def classify_candidate_image_without_vlm(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Local rule-based image classification function.

    No Visual Large Model is invoked in this stage, so any image that passes basic quality screening
    and high-confidence landscape filtering is marked as candidate_outfit.

    Why not strictly determine "landscape / text screenshot / marketing" here?
    Because relying solely on rules like dimensions, ratio, hash can easily cause misjudgments.
    For example:
    - A vertical image might be an outfit photo, or a long screenshot
    - A detailed image might be valid clothing details, or a product marketing image
    - Background scenery might contain character outfits and still be valuable for analysis

    Therefore, a conservative strategy is adopted in the current version:
    - Explicitly bad images are excluded first
    - High-confidence pure landscapes/empty scenes are excluded first
    - Suspicious but usable images first enter candidate_outfit
    - Finer classification is done later through Qwen-VL-Max or manual review

    Args:
        record:
            Image-level record.

    Returns:
        Dict[str, Any]:
            Quality screening results.
    """
    image_path = Path(record["image_path"])

    (
        passed,
        image_type,
        reject_reason,
        width,
        height,
        aspect_ratio,
        image_hash,
    ) = inspect_basic_image_quality(image_path)

    return {
        "Image_ID": record["Image_ID"],
        "note_id": record.get("note_id", ""),
        "image_path": str(image_path),
        "passed": passed,
        "image_type": image_type,
        "reject_reason": reject_reason,
        "confidence": 1.0 if passed else 0.0,
        "width": width,
        "height": height,
        "aspect_ratio": round(aspect_ratio, 4) if aspect_ratio is not None else "",
        "image_hash": image_hash or "",
        "duplicate_of": "",
    }


def run_quality_gatekeeper() -> List[Dict[str, Any]]:
    """
    Execute the main process of Node A Quality Gatekeeper.

    Process:
    1. Read image-level records from dataset_loader
    2. Perform basic quality checks for each image
    3. Perform duplicate detection on images that pass basic checks
    4. Save CSV
    5. Save JSON log

    Returns:
        List[Dict[str, Any]]:
            Quality screening results for each image.
    """
    ensure_output_dirs()

    image_records = load_image_records(save_index=True)

    results: List[Dict[str, Any]] = []

    # Only store hashes of "images that passed the screening".
    # If an image has already been rejected, it doesn't participate in subsequent duplicate checking.
    accepted_hashes: Dict[str, str] = {}

    for record in image_records:
        result = classify_candidate_image_without_vlm(record)

        # If the image passes basic quality screening, check if it's a suspected duplicate.
        if result["passed"] and result["image_hash"]:
            duplicate_of = find_duplicate_hash(
                current_hash=result["image_hash"],
                existing_hashes=accepted_hashes,
            )

            if duplicate_of is not None:
                result["passed"] = False
                result["image_type"] = IMAGE_TYPE_DUPLICATE
                result["reject_reason"] = "near_duplicate_image"
                result["confidence"] = 0.0
                result["duplicate_of"] = duplicate_of
            else:
                accepted_hashes[result["Image_ID"]] = result["image_hash"]

        results.append(result)

    save_quality_filtered_csv(results)
    save_quality_filter_log(results)

    return results


def save_quality_filtered_csv(
    results: List[Dict[str, Any]],
    output_path: Path = QUALITY_FILTERED_CSV,
) -> None:
    """
    Save the quality screening results CSV for Node A.

    Required output for course task:
        quality_filtered_images.csv

    Must contain:
        Image_ID
        passed (whether it passed screening)

    Extra fields like image_path, image_type, reject_reason, dimensions, etc., are kept here
    for convenience of subsequent reading by Node B, and for phased results presentation in Week 6.

    Args:
        results:
            List of quality screening results.
        output_path:
            CSV output path.
    """
    fieldnames = [
        "Image_ID",
        "note_id",
        "image_path",
        "passed",
        "image_type",
        "reject_reason",
        "confidence",
        "width",
        "height",
        "aspect_ratio",
        "duplicate_of",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow({key: result.get(key, "") for key in fieldnames})


def save_quality_filter_log(
    results: List[Dict[str, Any]],
    output_path: Path = QUALITY_FILTER_LOG_JSON,
) -> None:
    """
    Save the statistical log JSON for Node A.

    The log is used to answer key questions in course phased presentations:
    - How many images are there in the original Dataset v0?
    - How many were kept by Node A?
    - How many were filtered?
    - What are the reasons for filtering respectively?

    Args:
        results:
            List of quality screening results.
        output_path:
            JSON log output path.
    """
    total_images = len(results)
    passed_count = sum(1 for item in results if item["passed"])
    rejected_count = total_images - passed_count

    image_type_counter = Counter(item["image_type"] for item in results)

    reject_reason_counter = Counter(
        item["reject_reason"]
        for item in results
        if not item["passed"] and item.get("reject_reason")
    )

    log_data = {
        "node": "Node A - Quality Gatekeeper",
        "version": "local_rule_based_v1",
        "description": (
            "This version uses local rules to complete basic quality gatekeeping, including file existence, image readability, "
            "size, aspect ratio, and suspected duplicate detection. Fine-grained classification like full-body/half-body Outfit, "
            "text screenshots, landscapes, marketing images, etc., are recommended to access Qwen-VL-Max or CLIP in subsequent versions."
        ),
        "total_images": total_images,
        "passed": passed_count,
        "rejected": rejected_count,
        "image_type_breakdown": dict(image_type_counter),
        "rejection_breakdown": dict(reject_reason_counter),
        "output_csv": str(QUALITY_FILTERED_CSV),
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    """
    Allow direct execution of Node A:

        python node_a_quality_gatekeeper.py

    After running, it will generate:
        output/image_index.csv
        output/quality_filtered_images.csv
        output/quality_filter_log.json
    """
    final_results = run_quality_gatekeeper()

    total = len(final_results)
    passed = sum(1 for item in final_results if item["passed"])
    rejected = total - passed

    print("Node A quality gatekeeping completed.")
    print(f"Total images: {total}")
    print(f"Passed screening: {passed}")
    print(f"Filtered amount: {rejected}")
    print(f"Result CSV: {QUALITY_FILTERED_CSV}")
    print(f"Log JSON: {QUALITY_FILTER_LOG_JSON}")
