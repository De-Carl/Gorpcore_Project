"""
Node B: Vision-LLM Annotator.

Node Objective:
Read the images after Node A quality gating, call the Qwen-VL-Max multimodal model,
and generate structured JSON labels for each screened Gorpcore outfit image.

Input:
    Gorpcore_Agent/output/quality_filtered_images.csv

Output:
    Gorpcore_Agent/output/json_labels/{Image_ID}.json
    Gorpcore_Agent/output/annotation_errors.csv
    Gorpcore_Agent/output/vision_curation_log.csv

Target model output format:

{
  "Image_ID": "GRP-XHS-xxx-01",
  "Curation_Status": "use",
  "Image_Category": "full_body_outfit",
  "Reject_Reason": "none",
  "Body_Coverage": "full_body",
  "Text_Overlay_Level": "none",
  "Outfit_Count": 1,
  "Main_Subject_Visibility": "clear",
  "Pockets": 2,
  "Zipper_Type": "Sealed",
  "Fit": "Loose",
  "Reflective": true,
  "Primary_Color": "black",
  "Secondary_Color": "olive green",
  "Material_Clue": ["matte nylon", "ripstop"],
  "Scenario": "Urban_Commute",
  "Visual_Weight": "lightweight",
  "Gorpcore_Relevance": 0.87,
  "Confidence": 0.82
}

Note:
1. API Key should not be hardcoded in the code.
2. Please set the environment variable DASHSCOPE_API_KEY before running.
3. This script uses the OpenAI compatible interface of Alibaba Cloud Bailian DashScope.
"""

import base64
import csv
import json
import os
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI

from config import (
    JSON_LABEL_DIR,
    OUTPUT_DIR,
    QUALITY_FILTERED_CSV,
    ensure_output_dirs,
)


# ============================================================
# 1. Node B Output File Configuration
# ============================================================

# Record images that failed to be annotated.
ANNOTATION_ERRORS_CSV = OUTPUT_DIR / "annotation_errors.csv"

# Record Node B curation judgment for easy manual review of use / reject / review.
CURATION_LOG_CSV = OUTPUT_DIR / "vision_curation_log.csv"

# Optional: Record Node B overall run log.
ANNOTATION_LOG_JSON = OUTPUT_DIR / "vision_annotation_log.json"


# ============================================================
# 2. Model and API Configuration
# ============================================================

# DashScope OpenAI compatible mode interface address.
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# The vision-language model used.
# qwen-vl-max is suitable for stronger image understanding and structured annotation.
VISION_MODEL_NAME = "qwen-vl-max"

# Interval seconds between each API request.
# Setting a brief sleep is to reduce the probability of triggering rate limits.
REQUEST_INTERVAL_SECONDS = 0.8

# If a picture already has a JSON annotation file, whether to skip it.
# True means supporting resuming from a breakpoint.
SKIP_EXISTING_LABELS = True


# ============================================================
# 3. Enum Values Configuration
# ============================================================

VALID_ZIPPER_TYPES = {"Sealed", "Exposed", "None", "Unclear"}
VALID_FIT_TYPES = {"Loose", "Regular", "Tight", "Oversized", "Cropped", "Unclear"}
VALID_CURATION_STATUS = {"use", "reject", "review"}
VALID_IMAGE_CATEGORIES = {
    "full_body_outfit",
    "half_body_outfit",
    "detail_closeup",
    "multi_panel_outfit",
    "text_overlay_outfit",
    "product_marketing",
    "landscape",
    "text_screenshot",
    "unrelated",
    "unclear",
}
VALID_REJECT_REASONS = {
    "none",
    "no_visible_outfit",
    "pure_landscape",
    "text_dominant",
    "product_only",
    "unrelated",
    "too_unclear",
}
VALID_BODY_COVERAGE = {
    "full_body",
    "upper_body",
    "lower_body",
    "partial_detail",
    "multiple",
    "none",
    "unclear",
}
VALID_TEXT_OVERLAY_LEVELS = {"none", "low", "medium", "high"}
VALID_MAIN_SUBJECT_VISIBILITY = {"clear", "partial", "small", "unclear", "none"}
VALID_SCENARIOS = {
    "Urban_Commute",
    "Outdoor",
    "Office",
    "Fashion_Street",
    "Sports",
    "Unclear",
}
VALID_VISUAL_WEIGHTS = {"lightweight", "medium", "heavyweight", "unclear"}


# ============================================================
# 4. Prompt Configuration
# ============================================================

SYSTEM_PROMPT = """
You are a professional fashion image curator and Gorpcore outfit analyst.

Your task has two stages:

Stage 1: Curate the image.
Decide whether this image is useful for outfit analysis.

Stage 2: If useful, extract structured visual labels only from visible clothing.
If not useful, return curation fields and set unclear/default values for fashion labels.

You must return strictly valid JSON only.
Do not include Markdown.
Do not include explanations.
Do not include code fences.

Required JSON schema:

{
  "Curation_Status": "use" | "reject" | "review",
  "Image_Category": "full_body_outfit" | "half_body_outfit" | "detail_closeup" | "multi_panel_outfit" | "text_overlay_outfit" | "product_marketing" | "landscape" | "text_screenshot" | "unrelated" | "unclear",
  "Reject_Reason": "none" | "no_visible_outfit" | "pure_landscape" | "text_dominant" | "product_only" | "unrelated" | "too_unclear",
  "Body_Coverage": "full_body" | "upper_body" | "lower_body" | "partial_detail" | "multiple" | "none" | "unclear",
  "Text_Overlay_Level": "none" | "low" | "medium" | "high",
  "Outfit_Count": integer,
  "Main_Subject_Visibility": "clear" | "partial" | "small" | "unclear" | "none",

  "Pockets": integer,
  "Zipper_Type": "Sealed" | "Exposed" | "None" | "Unclear",
  "Fit": "Loose" | "Regular" | "Tight" | "Oversized" | "Cropped" | "Unclear",
  "Reflective": boolean,
  "Primary_Color": string,
  "Secondary_Color": string,
  "Material_Clue": array of strings,
  "Scenario": "Urban_Commute" | "Outdoor" | "Office" | "Fashion_Street" | "Sports" | "Unclear",
  "Visual_Weight": "lightweight" | "medium" | "heavyweight" | "unclear",
  "Gorpcore_Relevance": number between 0 and 1,
  "Confidence": number between 0 and 1
}

Curating rules:
- Use full_body_outfit when a complete outfit is visible from head/torso to legs or shoes.
- Use half_body_outfit when only upper body or lower body is clearly visible.
- Use detail_closeup for close-up images of garments, pockets, zippers, fabric, shoes, bags, or technical details.
- Use multi_panel_outfit when the image contains multiple sub-images or collage panels showing outfits.
- Use text_overlay_outfit when text exists but the outfit is still visually analyzable.
- Reject pure landscape, text-dominant screenshots, unrelated images, and product-only images without a worn outfit.
- For product-only images, reject unless the clothing is clearly worn by a person or shown as a complete styled outfit.
- If the image is multi-panel, analyze the most visually clear and central outfit. Set Outfit_Count to the approximate number of visible outfits.
- If only a detail is visible, do not infer full outfit fit, scenario, or hidden garment features.
- If an image is useful but ambiguous, use Curation_Status "review" rather than forcing a confident label.

Field definitions:
- Pockets: approximate number of visible functional or three-dimensional pockets.
- Zipper_Type: identify whether visible zipper design is sealed, exposed, absent, or unclear.
- Fit: judge only the visible garment silhouette. Use "Unclear" when the body coverage is too partial.
- Reflective: true only if reflective strips or reflective technical details are clearly visible.
- Primary_Color: dominant clothing color.
- Secondary_Color: secondary or accent clothing color. Use "none" if not visible.
- Material_Clue: 1 to 4 visual material/style clues, such as matte nylon, ripstop, shell fabric, fleece, mesh, waterproof, technical.
- Scenario: most likely usage scenario shown by the outfit.
- Visual_Weight: visual judgment of clothing thickness or heaviness.
- Gorpcore_Relevance: how strongly the image matches Gorpcore or technical outdoor styling.
- Confidence: your confidence in this visual annotation.

Important rules:
- If the image is unclear, still return JSON and use "Unclear" or "unclear".
- Do not hallucinate hidden details.
- Only label what is visually supported by the image.
- For rejected images, set Reject_Reason to a specific non-none value, Gorpcore_Relevance to 0, and Confidence to your confidence in the rejection.
"""


# ============================================================
# 5. Basic Utility Functions
# ============================================================

def get_dashscope_client() -> OpenAI:
    """
    Initialize DashScope OpenAI compatible client.

    The API Key is read from the environment variable DASHSCOPE_API_KEY.
    It is not recommended to hardcode the API Key in the source code because:
    1. It's easy to leak
    2. It's not convenient for multi-person collaboration
    3. It does not comply with project ethics and security practices

    You can set it in Windows PowerShell like this:
        $env:DASHSCOPE_API_KEY="你的API_KEY"

    Returns:
        OpenAI:
            OpenAI compatible client.
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "Environment variable DASHSCOPE_API_KEY not detected. Please set the API Key first."
        )

    return OpenAI(
        api_key=api_key,
        base_url=DASHSCOPE_BASE_URL,
    )


def encode_image_to_base64(image_path: Path) -> str:
    """
    Encode the local image to a Base64 string.

    Qwen-VL-Max's OpenAI compatible interface supports using:
        data:image/jpeg;base64,...

    This method passes in the local image content directly.

    Parameters:
        image_path:
            Image path.

    Returns:
        str:
            Base64 encoded image string.
    """
    with image_path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def guess_mime_type(image_path: Path) -> str:
    """
    Infer the MIME type based on the image suffix.

    Parameters:
        image_path:
            Image path.

    Returns:
        str:
            MIME type string.
    """
    suffix = image_path.suffix.lower()

    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"

    if suffix == ".png":
        return "image/png"

    if suffix == ".webp":
        return "image/webp"

    # Default is processed as jpeg, because the current dataset is mostly jpg.
    return "image/jpeg"


def load_passed_images(csv_path: Path = QUALITY_FILTERED_CSV) -> List[Dict[str, str]]:
    """
    Read Node A output, and filter images with passed == true.

    Parameters:
        csv_path:
            Path to quality_filtered_images.csv.

    Returns:
        List[Dict[str, str]]:
            Image records that passed quality gating.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Cannot find Node A output file: {csv_path}。Please run node_a_quality_gatekeeper.py first."
        )

    passed_records: List[Dict[str, str]] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            passed_value = str(row.get("passed", "")).strip().lower()

            if passed_value == "true":
                passed_records.append(row)

    return passed_records


def label_output_path(image_id: str) -> Path:
    """
    Generate single image JSON label output path based on Image_ID.

    Parameters:
        image_id:
            Unique image ID.

    Returns:
        Path:
            JSON output path.
    """
    return JSON_LABEL_DIR / f"{image_id}.json"


# ============================================================
# 6. Model Call Function
# ============================================================

def call_vision_model(
    client: OpenAI,
    image_path: Path,
) -> Dict[str, Any]:
    """
    Call Qwen-VL-Max to perform visual annotation on a single image.

    Parameters:
        client:
            DashScope OpenAI compatible client.
        image_path:
            Image path.

    Returns:
        Dict[str, Any]:
            The JSON dictionary returned by the model and parsed.
    """
    base64_image = encode_image_to_base64(image_path)
    mime_type = guess_mime_type(image_path)

    response = client.chat.completions.create(
        model=VISION_MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        },
                    }
                ],
            },
        ],
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model return content is not valid JSON: {raw_content}") from e

    return parsed


# ============================================================
# 7. Label Normalization and Validation
# ============================================================

def clamp_float(value: Any, default: float = 0.0) -> float:
    """
    Convert input value to a decimal between 0 and 1.

    The model may sometimes return a string, such as "0.8"。
    Here it is uniformly converted to float, and the range is limited.

    Parameters:
        value:
            Any input value.
        default:
            The default value to use when conversion fails.

    Returns:
        float:
            A decimal between 0 and 1.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default

    if number < 0:
        return 0.0

    if number > 1:
        return 1.0

    return number


def normalize_bool(value: Any) -> bool:
    """
    Normalize the value returned by the model to boolean.

    The model usually returns true/false,
    but occasionally it may return "true"、"yes"、"no"。
    Compatibility processing is done here.

    Parameters:
        value:
            Any input value.

    Returns:
        bool:
            Boolean value.
    """
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in {"true", "yes", "1", "visible"}


def normalize_enum(value: Any, valid_values: set, default: str) -> str:
    """
    Normalize the enum field to the allowed range.

    Parameters:
        value:
            Model return value.
        valid_values:
            Allowed enum set.
        default:
            If the model return value is invalid, use this default value.

    Returns:
        str:
            Valid enum value.
    """
    text = str(value).strip()

    if text in valid_values:
        return text

    return default


def normalize_int(value: Any, default: int = 0, minimum: int = 0) -> int:
    """
    Normalize integer fields returned by the model.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default

    return max(minimum, number)


def normalize_material_clue(value: Any) -> List[str]:
    """
    Normalize the Material_Clue field.

    The target format is a string array.
    If the model returns a string, wrap it into a single-element array.
    If it is empty, return ["unclear"]。

    Parameters:
        value:
            Material_Clue returned by the model.

    Returns:
        List[str]:
            Material clue array.
    """
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        cleaned = [value.strip()]
    else:
        cleaned = []

    if not cleaned:
        return ["unclear"]

    # Keep up to 4 to avoid excessively long model output.
    return cleaned[:4]


def normalize_annotation(
    image_record: Dict[str, str],
    raw_label: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize the raw model output into the project's unified JSON label format.

    The significance of doing this:
    1. Ensure consistent fields in each JSON file
    2. Avoid occasional model output format fluctuations affecting subsequent Node C
    3. Supplement traceback fields like Image_ID, note_id, image_path

    Parameters:
        image_record:
            Image record from quality_filtered_images.csv.
        raw_label:
            Raw JSON returned by the model.

    Returns:
        Dict[str, Any]:
            Normalized label JSON.
    """
    curation_status = normalize_enum(
        raw_label.get("Curation_Status"),
        VALID_CURATION_STATUS,
        "review",
    )

    reject_reason = normalize_enum(
        raw_label.get("Reject_Reason"),
        VALID_REJECT_REASONS,
        "none" if curation_status == "use" else "too_unclear",
    )

    if curation_status == "reject" and reject_reason == "none":
        reject_reason = "too_unclear"

    normalized = {
        "Image_ID": image_record.get("Image_ID", ""),
        "note_id": image_record.get("note_id", ""),
        "image_path": image_record.get("image_path", ""),

        "Curation_Status": curation_status,
        "Image_Category": normalize_enum(
            raw_label.get("Image_Category"),
            VALID_IMAGE_CATEGORIES,
            "unclear",
        ),
        "Reject_Reason": reject_reason,
        "Body_Coverage": normalize_enum(
            raw_label.get("Body_Coverage"),
            VALID_BODY_COVERAGE,
            "unclear",
        ),
        "Text_Overlay_Level": normalize_enum(
            raw_label.get("Text_Overlay_Level"),
            VALID_TEXT_OVERLAY_LEVELS,
            "none",
        ),
        "Outfit_Count": normalize_int(raw_label.get("Outfit_Count"), default=0),
        "Main_Subject_Visibility": normalize_enum(
            raw_label.get("Main_Subject_Visibility"),
            VALID_MAIN_SUBJECT_VISIBILITY,
            "unclear",
        ),

        "Pockets": normalize_int(raw_label.get("Pockets"), default=0),
        "Zipper_Type": normalize_enum(
            raw_label.get("Zipper_Type"),
            VALID_ZIPPER_TYPES,
            "Unclear",
        ),
        "Fit": normalize_enum(
            raw_label.get("Fit"),
            VALID_FIT_TYPES,
            "Unclear",
        ),
        "Reflective": normalize_bool(raw_label.get("Reflective")),

        "Primary_Color": str(raw_label.get("Primary_Color", "unclear")).strip() or "unclear",
        "Secondary_Color": str(raw_label.get("Secondary_Color", "none")).strip() or "none",

        "Material_Clue": normalize_material_clue(raw_label.get("Material_Clue")),

        "Scenario": normalize_enum(
            raw_label.get("Scenario"),
            VALID_SCENARIOS,
            "Unclear",
        ),
        "Visual_Weight": normalize_enum(
            raw_label.get("Visual_Weight"),
            VALID_VISUAL_WEIGHTS,
            "unclear",
        ),

        "Gorpcore_Relevance": clamp_float(
            raw_label.get("Gorpcore_Relevance"),
            default=0.0,
        ),
        "Confidence": clamp_float(
            raw_label.get("Confidence"),
            default=0.0,
        ),

        # Save raw model output to facilitate troubleshooting and manual review.
        # If you later feel the file is too large, you can delete this item.
        "raw_model_output": raw_label,
    }

    return normalized


def save_json_label(label: Dict[str, Any]) -> None:
    """
    Save the JSON label of a single image.

    Parameters:
        label:
            Normalized label data.
    """
    image_id = label["Image_ID"]
    output_path = label_output_path(image_id)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(label, f, ensure_ascii=False, indent=2)


# ============================================================
# 8. Error Log and Run Log
# ============================================================

def save_annotation_errors(errors: List[Dict[str, str]]) -> None:
    """
    Save annotation failure records to CSV.

    Even if there are no errors, an empty CSV with headers will be generated,
    to prove that the script has run completely.

    Parameters:
        errors:
            List of error records.
    """
    fieldnames = [
        "Image_ID",
        "image_path",
        "error_type",
        "error_message",
    ]

    with ANNOTATION_ERRORS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for error in errors:
            writer.writerow({key: error.get(key, "") for key in fieldnames})


def build_curation_record(
    image_record: Dict[str, str],
    label: Optional[Dict[str, Any]] = None,
    run_status: str = "annotated",
) -> Dict[str, Any]:
    """
    Extract curation log fields from normalized labels.
    """
    label = label or {}

    return {
        "Image_ID": image_record.get("Image_ID", label.get("Image_ID", "")),
        "note_id": image_record.get("note_id", label.get("note_id", "")),
        "image_path": image_record.get("image_path", label.get("image_path", "")),
        "run_status": run_status,
        "Curation_Status": label.get("Curation_Status", ""),
        "Image_Category": label.get("Image_Category", ""),
        "Reject_Reason": label.get("Reject_Reason", ""),
        "Body_Coverage": label.get("Body_Coverage", ""),
        "Text_Overlay_Level": label.get("Text_Overlay_Level", ""),
        "Outfit_Count": label.get("Outfit_Count", ""),
        "Main_Subject_Visibility": label.get("Main_Subject_Visibility", ""),
        "Gorpcore_Relevance": label.get("Gorpcore_Relevance", ""),
        "Confidence": label.get("Confidence", ""),
    }


def load_existing_label(output_path: Path) -> Optional[Dict[str, Any]]:
    """
    Read existing JSON labels to supplement curation logs when resuming from a breakpoint.
    """
    try:
        with output_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def save_curation_log(curation_records: List[Dict[str, Any]]) -> None:
    """
    Save Node B curation results to CSV for easy manual review.
    """
    fieldnames = [
        "Image_ID",
        "note_id",
        "image_path",
        "run_status",
        "Curation_Status",
        "Image_Category",
        "Reject_Reason",
        "Body_Coverage",
        "Text_Overlay_Level",
        "Outfit_Count",
        "Main_Subject_Visibility",
        "Gorpcore_Relevance",
        "Confidence",
    ]

    with CURATION_LOG_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for record in curation_records:
            writer.writerow({key: record.get(key, "") for key in fieldnames})


def save_annotation_log(
    total_candidates: int,
    annotated_count: int,
    skipped_count: int,
    error_count: int,
    curation_records: List[Dict[str, Any]],
) -> None:
    """
    Save Node B run statistics log.

    Parameters:
        total_candidates:
            Total number of candidate images passed Node A screening.
        annotated_count:
            Number of successful new annotations this time.
        skipped_count:
            Number skipped due to existing JSON files.
        error_count:
            Number of failed annotations.
    """
    curation_status_counter = Counter(
        str(item.get("Curation_Status", "")).strip() or "unknown"
        for item in curation_records
    )
    image_category_counter = Counter(
        str(item.get("Image_Category", "")).strip() or "unknown"
        for item in curation_records
    )
    reject_reason_counter = Counter(
        str(item.get("Reject_Reason", "")).strip() or "unknown"
        for item in curation_records
        if str(item.get("Curation_Status", "")).strip() == "reject"
    )

    log_data = {
        "node": "Node B - Vision-LLM Annotator",
        "model": VISION_MODEL_NAME,
        "total_candidates": total_candidates,
        "annotated_count": annotated_count,
        "skipped_existing": skipped_count,
        "error_count": error_count,
        "curation_status_breakdown": dict(curation_status_counter),
        "image_category_breakdown": dict(image_category_counter),
        "reject_reason_breakdown": dict(reject_reason_counter),
        "json_label_dir": str(JSON_LABEL_DIR),
        "annotation_errors_csv": str(ANNOTATION_ERRORS_CSV),
        "curation_log_csv": str(CURATION_LOG_CSV),
    }

    with ANNOTATION_LOG_JSON.open("w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


# ============================================================
# 9. Node B Main Process
# ============================================================

def run_vision_annotator(limit: Optional[int] = None) -> None:
    """
    Execute Node B batch visual annotation.

    Parameters:
        limit:
            Optional parameter to limit the number of images processed this time.
            For example, pass limit=5 when debugging to annotate only the first 5 images.
            Pass None during official run to indicate processing all images that passed Node A.
    """
    ensure_output_dirs()

    passed_images = load_passed_images()

    if limit is not None:
        passed_images = passed_images[:limit]

    client = get_dashscope_client()

    errors: List[Dict[str, str]] = []
    curation_records: List[Dict[str, Any]] = []

    annotated_count = 0
    skipped_count = 0

    for index, image_record in enumerate(passed_images, start=1):
        image_id = image_record.get("Image_ID", "")
        image_path = Path(image_record.get("image_path", ""))

        output_path = label_output_path(image_id)

        print(f"[{index}/{len(passed_images)}] Annotating: {image_id}")

        if SKIP_EXISTING_LABELS and output_path.exists():
            print(f"  JSON label already exists, skipping: {output_path}")
            existing_label = load_existing_label(output_path)
            curation_records.append(
                build_curation_record(
                    image_record=image_record,
                    label=existing_label,
                    run_status="skipped_existing",
                )
            )
            skipped_count += 1
            continue

        if not image_path.exists():
            curation_records.append(
                build_curation_record(
                    image_record=image_record,
                    run_status="missing_file",
                )
            )
            errors.append(
                {
                    "Image_ID": image_id,
                    "image_path": str(image_path),
                    "error_type": "missing_file",
                    "error_message": "Image file does not exist",
                }
            )
            print("  Failed: Image file does not exist")
            continue

        try:
            raw_label = call_vision_model(client, image_path)
            normalized_label = normalize_annotation(image_record, raw_label)
            save_json_label(normalized_label)
            curation_records.append(
                build_curation_record(
                    image_record=image_record,
                    label=normalized_label,
                    run_status="annotated",
                )
            )

            annotated_count += 1
            print(f"  Successfully saved: {output_path}")

        except Exception as e:
            curation_records.append(
                build_curation_record(
                    image_record=image_record,
                    run_status="error",
                )
            )
            errors.append(
                {
                    "Image_ID": image_id,
                    "image_path": str(image_path),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            print(f"  Annotation failed: {type(e).__name__}: {e}")

        time.sleep(REQUEST_INTERVAL_SECONDS)

    save_annotation_errors(errors)
    save_curation_log(curation_records)

    save_annotation_log(
        total_candidates=len(passed_images),
        annotated_count=annotated_count,
        skipped_count=skipped_count,
        error_count=len(errors),
        curation_records=curation_records,
    )

    print("Node B visual annotation completed.")
    print(f"Candidate images: {len(passed_images)}")
    print(f"Successfully newly annotated: {annotated_count}")
    print(f"Skipped existing annotations: {skipped_count}")
    print(f"Failure count: {len(errors)}")
    print(f"JSON output directory: {JSON_LABEL_DIR}")
    print(f"Error log: {ANNOTATION_ERRORS_CSV}")
    print(f"Curation log: {CURATION_LOG_CSV}")


if __name__ == "__main__":
    """
    Direct run method:

        python node_b_vision_annotator.py

    Debugging suggestion:
    You can change None below to 3 or 5 to run only a few images, and run in full after confirming the API is normal.

        run_vision_annotator(limit=5)
    """
    run_vision_annotator(limit=3)
