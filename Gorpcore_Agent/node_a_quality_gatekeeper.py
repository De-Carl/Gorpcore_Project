"""
Node A: Quality Gatekeeper 质量门控节点。

本节点目标：
从 Dataset v0 的图片中筛选出适合进入后续视觉标注阶段的候选图像。

根据项目文档和课程要求，Node A 需要完成：

1. 读取 Dataset v0 图像
2. 保留完整/半身 Outfit 图片
3. 删除文本截图、风景图和营销重复
4. 输出 quality_filtered_images.csv
5. 输出日志文件，记录过滤条目数量和类型

当前版本说明：
本脚本先实现“本地规则版”质量门控，不依赖外部 API。
它可以稳定完成以下筛选：

- 文件不存在
- 图片损坏
- 图片尺寸过小
- 图片宽高比异常
- 疑似重复图片

对于“完整/半身 Outfit、文本截图、风景图、营销图”的更细分类，
本地规则无法非常可靠地判断，因此当前统一把通过基础质量筛选的图片
标记为 candidate_outfit。

后续可以在本脚本中新增 VLM 判断逻辑，例如：
    classify_image_with_vlm(image_path)

让 Qwen-VL-Max 输出：
    full_body_outfit / half_body_outfit / text_screenshot / landscape / product_marketing

这样就能进一步满足更精细的质量门控要求。
"""

import csv
import json
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any ,Optional, Tuple
from PIL import Image, UnidentifiedImageError

from config import (
    DUPLICATE_HASH_DISTANCE,
    HASH_SIZE,
    IMAGE_TYPE_BAD_RATIO,
    IMAGE_TYPE_CORRUPTED,
    IMAGE_TYPE_DUPLICATE,
    IMAGE_TYPE_MISSING,
    IMAGE_TYPE_TOO_SMALL,
    IMAGE_TYPE_VALID,
    MAX_ASPECT_RATIO,
    MIN_ASPECT_RATIO,
    MIN_IMAGE_HEIGHT,
    MIN_IMAGE_WIDTH,
    QUALITY_FILTER_LOG_JSON,
    QUALITY_FILTERED_CSV,
    ensure_output_dirs,
)

from data_loader import load_image_records


def compute_average_hash(image: Image.Image, hash_size: int=HASH_SIZE) -> str:
    """
    计算图片的平均哈希 average hash。

    average hash 是一种简单的感知哈希方法：
    1. 将图片缩小成 hash_size x hash_size
    2. 转成灰度图
    3. 计算所有像素的平均值
    4. 每个像素大于等于平均值记为 1，否则记为 0
    5. 最终得到一个 0/1 字符串

    两张图如果视觉内容非常接近，它们的 hash 通常也会很接近。
    因此可以用来做“疑似重复图片”过滤。

    参数:
        image:
            PIL Image 对象。
        hash_size:
            哈希尺寸，默认来自 config.py。

    返回:
        str:
            由 0 和 1 组成的哈希字符串，例如长度为 64。
    """
    gray_image = image.convert("L").resize((hash_size, hash_size)) # 转成灰度图并缩放
    pixels = list(gray_image.getdata()) # 获取像素值列表
    avg_pixel = sum(pixels) / len(pixels) # 计算平均像素值

    bits = ["1" if pixel >= avg_pixel else "0" for pixel in pixels] # 根据平均值生成 0/1 字符串
    return "".join(bits)

def hamming_distance(hash_a: str, hash_b: str) -> int:
    """
    计算两个哈希字符串之间的汉明距离。

    汉明距离表示两个字符串相同位置上不同字符的数量。
    对于图片 hash 来说，距离越小，说明图片越相似。

    参数:
        hash_a:
            第一个 hash 字符串。
        hash_b:
            第二个 hash 字符串。

    返回:
        int:
            汉明距离。
    """
    if len(hash_a) != len(hash_b):
        raise ValueError("两个 hash 的长度不一致，无法计算汉明距离。")

    return sum(char_a != char_b for char_a, char_b in zip(hash_a, hash_b))

def find_duplicate_hash(
    current_hash: str,
    existing_hashes: Dict[str, str],
    threshold: int = DUPLICATE_HASH_DISTANCE,
) -> Optional[str]:
    """
    判断当前图片是否与已有图片疑似重复。

    参数:
        current_hash:
            当前图片的 average hash。
        existing_hashes:
            已通过筛选的图片 hash 字典。
            key 是 Image_ID，value 是图片 hash。
        threshold:
            汉明距离阈值。
            小于等于该值时，认为当前图与已有图重复。

    返回:
        Optional[str]:
            如果发现重复，返回与其重复的已有 Image_ID。
            如果没有重复，返回 None。
    """
    for existing_image_id, existing_hash in existing_hashes.items():
        distance = hamming_distance(current_hash, existing_hash)

        if distance <= threshold:
            return existing_image_id

    return None

def inspect_basic_image_quality(
    image_path: Path,
) -> Tuple[bool, str, Optional[str], Optional[int], Optional[int], Optional[float], Optional[str]]:
    """
    检查图片基础质量。

    本函数只做“确定性强”的基础检查：
    - 文件是否存在
    - 图片是否能被 PIL 打开
    - 图片宽高是否足够
    - 图片宽高比是否在合理范围

    参数:
        image_path:
            图片绝对路径。

    返回:
        Tuple:
            passed:
                是否通过基础质量检查。
            image_type:
                图片类型标签。
            reject_reason:
                如果未通过，记录拒绝原因；如果通过，则为 None。
            width:
                图片宽度。
            height:
                图片高度。
            aspect_ratio:
                图片宽高比。
            image_hash:
                图片 average hash；如果图片无法打开，则为 None。
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
            # load() 会强制读取图片数据。
            # 某些损坏图片可能在 open 阶段不报错，但 load 阶段会报错。
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
    本地规则版图片分类函数。

    当前阶段没有调用视觉大模型，因此只要图片通过基础质量筛选，
    就将其标记为 candidate_outfit。

    为什么不在这里强行判断“风景图/文本截图/营销图”？
    因为单靠尺寸、比例、hash 等规则很容易误判。
    比如：
    - 竖图可能是穿搭照，也可能是长截图
    - 细节图可能是有效服装细节，也可能是商品营销图
    - 背景风景中有人物穿搭，仍可能有分析价值

    所以当前版本采用保守策略：
    - 明确坏图先排除
    - 可疑但可用的图先进入 candidate_outfit
    - 后续通过 Qwen-VL-Max 或人工复核做更精细分类

    参数:
        record:
            图片级记录。

    返回:
        Dict[str, Any]:
            质量筛选结果。
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
    执行 Node A 质量门控主流程。

    流程：
    1. 从 dataset_loader 读取图片级 records
    2. 对每张图做基础质量检查
    3. 对通过基础检查的图做重复检测
    4. 保存 CSV
    5. 保存 JSON 日志

    返回:
        List[Dict[str, Any]]:
            每张图片的质量筛选结果。
    """
    ensure_output_dirs()

    image_records = load_image_records(save_index=True)

    results: List[Dict[str, Any]] = []

    # 只保存“已通过筛选图片”的 hash。
    # 如果某张图本身已经被拒绝，就不参与后续重复判断。
    accepted_hashes: Dict[str, str] = {}

    for record in image_records:
        result = classify_candidate_image_without_vlm(record)

        # 如果图片通过基础质量筛选，再检查是否疑似重复。
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
    保存 Node A 的质量筛选结果 CSV。

    课程任务要求输出：
        quality_filtered_images.csv

    必须包含：
        Image_ID
        是否通过筛选

    这里额外保留 image_path、image_type、reject_reason、尺寸等字段，
    方便后续 Node B 读取，也方便 Week 6 展示阶段性结果。

    参数:
        results:
            质量筛选结果列表。
        output_path:
            CSV 输出路径。
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
    保存 Node A 的统计日志 JSON。

    日志用于回答课程阶段展示中的关键问题：
    - 原始 Dataset v0 有多少张图？
    - Node A 保留了多少张？
    - 过滤了多少张？
    - 过滤原因分别是什么？

    参数:
        results:
            质量筛选结果列表。
        output_path:
            JSON 日志输出路径。
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
            "本版本使用本地规则完成基础质量门控，包括文件存在性、图片可读性、"
            "尺寸、宽高比和疑似重复检测。完整/半身 Outfit、文本截图、风景图、"
            "营销图等细粒度分类建议在后续版本中接入 Qwen-VL-Max 或 CLIP。"
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
    允许直接运行 Node A：

        python node_a_quality_gatekeeper.py

    运行后会生成：
        output/image_index.csv
        output/quality_filtered_images.csv
        output/quality_filter_log.json
    """
    final_results = run_quality_gatekeeper()

    total = len(final_results)
    passed = sum(1 for item in final_results if item["passed"])
    rejected = total - passed

    print("Node A 质量门控完成。")
    print(f"总图片数: {total}")
    print(f"通过筛选: {passed}")
    print(f"过滤数量: {rejected}")
    print(f"结果 CSV: {QUALITY_FILTERED_CSV}")
    print(f"日志 JSON: {QUALITY_FILTER_LOG_JSON}")