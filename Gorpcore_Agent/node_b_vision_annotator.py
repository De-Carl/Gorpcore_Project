"""
Node B: Vision-LLM Annotator 视觉标注节点。

本节点目标：
读取 Node A 质量门控后的图片，调用 Qwen-VL-Max 多模态模型，
为每张通过筛选的 Gorpcore / 机能风穿搭图片生成结构化 JSON 标签。

输入：
    Gorpcore_Agent/output/quality_filtered_images.csv

输出：
    Gorpcore_Agent/output/json_labels/{Image_ID}.json
    Gorpcore_Agent/output/annotation_errors.csv

模型输出目标格式：

{
  "Image_ID": "GRP-XHS-xxx-01",
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

注意：
1. API Key 不应写死在代码中。
2. 请在运行前设置环境变量 DASHSCOPE_API_KEY。
3. 本脚本使用阿里云百炼 DashScope 的 OpenAI 兼容接口。
"""

import base64
import csv
import json
import os
import time
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
# 1. Node B 输出文件配置
# ============================================================

# 记录标注失败的图片。
ANNOTATION_ERRORS_CSV = OUTPUT_DIR / "annotation_errors.csv"

# 可选：记录 Node B 总体运行日志。
ANNOTATION_LOG_JSON = OUTPUT_DIR / "vision_annotation_log.json"


# ============================================================
# 2. 模型与 API 配置
# ============================================================

# DashScope OpenAI 兼容模式接口地址。
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 使用的视觉语言模型。
# qwen-vl-max 适合做较强的图片理解与结构化标注。
VISION_MODEL_NAME = "qwen-vl-max"

# 每次 API 请求之间的间隔秒数。
# 设置短暂 sleep 是为了降低触发限流的概率。
REQUEST_INTERVAL_SECONDS = 0.8

# 如果某张图片已经有 JSON 标注文件，是否跳过。
# True 表示支持断点续跑。
SKIP_EXISTING_LABELS = True


# ============================================================
# 3. 枚举值配置
# ============================================================

VALID_ZIPPER_TYPES = {"Sealed", "Exposed", "None", "Unclear"}
VALID_FIT_TYPES = {"Loose", "Regular", "Tight", "Oversized", "Cropped", "Unclear"}
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
# 4. Prompt 配置
# ============================================================

SYSTEM_PROMPT = """
You are a professional fashion data analyst and clothing curation expert.

Your task is to analyze one Gorpcore or technical outfit image and extract structured visual labels.

You must return strictly valid JSON only.
Do not include Markdown.
Do not include explanations.
Do not include code fences.

Required JSON schema:

{
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

Field definitions:
- Pockets: approximate number of visible functional or three-dimensional pockets.
- Zipper_Type: identify whether visible zipper design is sealed, exposed, absent, or unclear.
- Fit: judge the overall garment silhouette.
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
"""


# ============================================================
# 5. 基础工具函数
# ============================================================

def get_dashscope_client() -> OpenAI:
    """
    初始化 DashScope OpenAI 兼容客户端。

    API Key 从环境变量 DASHSCOPE_API_KEY 读取。
    不建议把 API Key 写死在源码中，因为：
    1. 容易泄露
    2. 不方便多人协作
    3. 不符合项目伦理与安全实践

    Windows PowerShell 中可以这样设置：
        $env:DASHSCOPE_API_KEY="你的API_KEY"

    返回:
        OpenAI:
            OpenAI 兼容客户端。
    """
    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "未检测到环境变量 DASHSCOPE_API_KEY。请先设置 API Key。"
        )

    return OpenAI(
        api_key=api_key,
        base_url=DASHSCOPE_BASE_URL,
    )


def encode_image_to_base64(image_path: Path) -> str:
    """
    将本地图片编码为 Base64 字符串。

    Qwen-VL-Max 的 OpenAI 兼容接口支持使用：
        data:image/jpeg;base64,...

    这种方式直接传入本地图片内容。

    参数:
        image_path:
            图片路径。

    返回:
        str:
            Base64 编码后的图片字符串。
    """
    with image_path.open("rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def guess_mime_type(image_path: Path) -> str:
    """
    根据图片后缀推断 MIME 类型。

    参数:
        image_path:
            图片路径。

    返回:
        str:
            MIME 类型字符串。
    """
    suffix = image_path.suffix.lower()

    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"

    if suffix == ".png":
        return "image/png"

    if suffix == ".webp":
        return "image/webp"

    # 默认按 jpeg 处理，因为当前数据集主要是 jpg。
    return "image/jpeg"


def load_passed_images(csv_path: Path = QUALITY_FILTERED_CSV) -> List[Dict[str, str]]:
    """
    读取 Node A 输出，并筛选 passed == true 的图片。

    参数:
        csv_path:
            quality_filtered_images.csv 路径。

    返回:
        List[Dict[str, str]]:
            通过质量门控的图片记录。
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"找不到 Node A 输出文件: {csv_path}。请先运行 node_a_quality_gatekeeper.py"
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
    根据 Image_ID 生成单图 JSON 标签输出路径。

    参数:
        image_id:
            图片唯一 ID。

    返回:
        Path:
            JSON 输出路径。
    """
    return JSON_LABEL_DIR / f"{image_id}.json"


# ============================================================
# 6. 模型调用函数
# ============================================================

def call_vision_model(
    client: OpenAI,
    image_path: Path,
) -> Dict[str, Any]:
    """
    调用 Qwen-VL-Max 对单张图片进行视觉标注。

    参数:
        client:
            DashScope OpenAI 兼容客户端。
        image_path:
            图片路径。

    返回:
        Dict[str, Any]:
            模型返回并解析后的 JSON 字典。
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
        raise ValueError(f"模型返回内容不是合法 JSON: {raw_content}") from e

    return parsed


# ============================================================
# 7. 标签规范化与校验
# ============================================================

def clamp_float(value: Any, default: float = 0.0) -> float:
    """
    将输入值转换为 0 到 1 之间的小数。

    模型有时可能返回字符串，例如 "0.8"。
    这里统一转成 float，并限制范围。

    参数:
        value:
            任意输入值。
        default:
            转换失败时使用的默认值。

    返回:
        float:
            0 到 1 之间的小数。
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
    将模型返回的值规范化为 boolean。

    模型通常会返回 true/false，
    但偶尔也可能返回 "true"、"yes"、"no"。
    这里做兼容处理。

    参数:
        value:
            任意输入值。

    返回:
        bool:
            布尔值。
    """
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in {"true", "yes", "1", "visible"}


def normalize_enum(value: Any, valid_values: set, default: str) -> str:
    """
    将枚举字段规范化到允许范围内。

    参数:
        value:
            模型返回值。
        valid_values:
            允许的枚举集合。
        default:
            如果模型返回值不合法，使用该默认值。

    返回:
        str:
            合法枚举值。
    """
    text = str(value).strip()

    if text in valid_values:
        return text

    return default


def normalize_material_clue(value: Any) -> List[str]:
    """
    规范化 Material_Clue 字段。

    目标格式是字符串数组。
    如果模型返回字符串，则包装成单元素数组。
    如果为空，则返回 ["unclear"]。

    参数:
        value:
            模型返回的 Material_Clue。

    返回:
        List[str]:
            材料线索数组。
    """
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str) and value.strip():
        cleaned = [value.strip()]
    else:
        cleaned = []

    if not cleaned:
        return ["unclear"]

    # 最多保留 4 个，避免模型输出过长。
    return cleaned[:4]


def normalize_annotation(
    image_record: Dict[str, str],
    raw_label: Dict[str, Any],
) -> Dict[str, Any]:
    """
    将模型原始输出规范化为项目统一 JSON 标签格式。

    这样做的意义：
    1. 保证每个 JSON 文件字段一致
    2. 避免模型偶发输出格式波动影响后续 Node C
    3. 将 Image_ID、note_id、image_path 等追溯字段补进去

    参数:
        image_record:
            来自 quality_filtered_images.csv 的图片记录。
        raw_label:
            模型返回的原始 JSON。

    返回:
        Dict[str, Any]:
            规范化后的标签 JSON。
    """
    pockets_raw = raw_label.get("Pockets", 0)

    try:
        pockets = int(pockets_raw)
    except (TypeError, ValueError):
        pockets = 0

    if pockets < 0:
        pockets = 0

    normalized = {
        "Image_ID": image_record.get("Image_ID", ""),
        "note_id": image_record.get("note_id", ""),
        "image_path": image_record.get("image_path", ""),

        "Pockets": pockets,
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

        # 保存模型原始输出，方便排查和人工复核。
        # 如果后续觉得文件太大，可以删除这一项。
        "raw_model_output": raw_label,
    }

    return normalized


def save_json_label(label: Dict[str, Any]) -> None:
    """
    保存单张图片的 JSON 标签。

    参数:
        label:
            规范化后的标签数据。
    """
    image_id = label["Image_ID"]
    output_path = label_output_path(image_id)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(label, f, ensure_ascii=False, indent=2)


# ============================================================
# 8. 错误日志与运行日志
# ============================================================

def save_annotation_errors(errors: List[Dict[str, str]]) -> None:
    """
    保存标注失败记录到 CSV。

    即使没有错误，也会生成一个带表头的空 CSV，
    方便证明脚本完整运行过。

    参数:
        errors:
            错误记录列表。
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


def save_annotation_log(
    total_candidates: int,
    annotated_count: int,
    skipped_count: int,
    error_count: int,
) -> None:
    """
    保存 Node B 运行统计日志。

    参数:
        total_candidates:
            Node A 通过筛选的候选图片总数。
        annotated_count:
            本次成功新增标注数量。
        skipped_count:
            因已有 JSON 文件而跳过的数量。
        error_count:
            标注失败数量。
    """
    log_data = {
        "node": "Node B - Vision-LLM Annotator",
        "model": VISION_MODEL_NAME,
        "total_candidates": total_candidates,
        "annotated_count": annotated_count,
        "skipped_existing": skipped_count,
        "error_count": error_count,
        "json_label_dir": str(JSON_LABEL_DIR),
        "annotation_errors_csv": str(ANNOTATION_ERRORS_CSV),
    }

    with ANNOTATION_LOG_JSON.open("w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


# ============================================================
# 9. Node B 主流程
# ============================================================

def run_vision_annotator(limit: Optional[int] = None) -> None:
    """
    执行 Node B 批量视觉标注。

    参数:
        limit:
            可选参数，用于限制本次处理图片数量。
            例如调试时传入 limit=5，只标注前 5 张。
            正式运行时传入 None，表示处理全部通过 Node A 的图片。
    """
    ensure_output_dirs()

    passed_images = load_passed_images()

    if limit is not None:
        passed_images = passed_images[:limit]

    client = get_dashscope_client()

    errors: List[Dict[str, str]] = []

    annotated_count = 0
    skipped_count = 0

    for index, image_record in enumerate(passed_images, start=1):
        image_id = image_record.get("Image_ID", "")
        image_path = Path(image_record.get("image_path", ""))

        output_path = label_output_path(image_id)

        print(f"[{index}/{len(passed_images)}] 正在标注: {image_id}")

        if SKIP_EXISTING_LABELS and output_path.exists():
            print(f"  已存在 JSON 标签，跳过: {output_path}")
            skipped_count += 1
            continue

        if not image_path.exists():
            errors.append(
                {
                    "Image_ID": image_id,
                    "image_path": str(image_path),
                    "error_type": "missing_file",
                    "error_message": "图片文件不存在",
                }
            )
            print("  失败：图片文件不存在")
            continue

        try:
            raw_label = call_vision_model(client, image_path)
            normalized_label = normalize_annotation(image_record, raw_label)
            save_json_label(normalized_label)

            annotated_count += 1
            print(f"  成功保存: {output_path}")

        except Exception as e:
            errors.append(
                {
                    "Image_ID": image_id,
                    "image_path": str(image_path),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
            )
            print(f"  标注失败: {type(e).__name__}: {e}")

        time.sleep(REQUEST_INTERVAL_SECONDS)

    save_annotation_errors(errors)

    save_annotation_log(
        total_candidates=len(passed_images),
        annotated_count=annotated_count,
        skipped_count=skipped_count,
        error_count=len(errors),
    )

    print("Node B 视觉标注完成。")
    print(f"候选图片数: {len(passed_images)}")
    print(f"新增成功标注: {annotated_count}")
    print(f"跳过已有标注: {skipped_count}")
    print(f"失败数量: {len(errors)}")
    print(f"JSON 输出目录: {JSON_LABEL_DIR}")
    print(f"错误日志: {ANNOTATION_ERRORS_CSV}")


if __name__ == "__main__":
    """
    直接运行方式：

        python node_b_vision_annotator.py

    调试建议：
    可以先把下面的 None 改成 3 或 5，只跑几张图片，确认 API 正常后再全量运行。

        run_vision_annotator(limit=5)
    """
    run_vision_annotator(limit=3)
