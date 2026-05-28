# config.py


"""
项目统一配置文件。

这个文件专门用于集中管理路径、输出目录、质量筛选阈值等配置。
后续 Node A / Node B / Node C / Node D 都应该优先从这里读取配置，
避免每个脚本里重复写路径，方便统一修改和维护。

当前项目目录大致为：

E:/code/Project/
  Dataset/
    xhs/
      xiaohongshu_with_images.json
      xiaohongshu_images/
        Gorpcore/
        机能风穿搭/
  Gorpcore_Agent/
    config.py
    dataset_loader.py
    node_a_quality_gatekeeper.py
    output/
"""

from pathlib import Path


# ============================================================
# 1. 项目根目录配置
# ============================================================

# 当前 config.py 位于 Gorpcore_Agent 目录下。
# parent 表示 Gorpcore_Agent 目录，parent.parent 表示项目根目录 Project。
# resolve() 用于获取绝对路径，避免相对路径带来的问题。
# Path 对象提供了方便的路径操作方法，推荐使用而不是字符串路径。
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Agent 代码目录。
AGENT_ROOT = PROJECT_ROOT / "Gorpcore_Agent"

# 数据集目录。
DATASET_ROOT = PROJECT_ROOT / "Dataset"

# 小红书原始 JSON 数据文件。
RAW_DATA_JSON = DATASET_ROOT / "xhs" / "xiaohongshu_with_images.json"

# 小红书数据工作目录。
# 注意：xiaohongshu_with_images.json 中的 downloaded_image_paths 通常是：
# xiaohongshu_images\机能风穿搭\xxx\image_01.jpg
# 实际完整路径需要拼到 Dataset/xhs/ 后面。
IMAGE_BASE_DIR = DATASET_ROOT / "xhs"

# 输出目录。
OUTPUT_DIR = AGENT_ROOT / "output"

# Node B 的 JSON 标签输出目录，虽然当前 Node A 暂时不用，
# 但提前放在 config 里，后面可以复用。
JSON_LABEL_DIR = OUTPUT_DIR / "json_labels"


# ============================================================
# 2. Node A 输出文件配置
# ============================================================

# Node A 输出：质量筛选结果 CSV。
QUALITY_FILTERED_CSV = OUTPUT_DIR / "quality_filtered_images.csv"

# Node A 输出：质量筛选日志 JSON。
QUALITY_FILTER_LOG_JSON = OUTPUT_DIR / "quality_filter_log.json"

# 可选输出：展开后的图片索引 CSV。
# 这个文件不是任务强制要求，但调试时很有用。
IMAGE_INDEX_CSV = OUTPUT_DIR / "image_index.csv"


# ============================================================
# 3. 图片基础质量筛选阈值
# ============================================================

# 最小图片宽度。
# 小于这个宽度的图通常信息量太低，可能是缩略图、加载失败图或无效图片。
MIN_IMAGE_WIDTH = 300

# 最小图片高度。
MIN_IMAGE_HEIGHT = 300

# 最大宽高比。
# 例如宽高比大于 3.5，可能是长截图、拼接图、横幅广告等。
MAX_ASPECT_RATIO = 3.5

# 最小宽高比。
# 例如宽高比小于 0.25，可能是极端长图或截图。
MIN_ASPECT_RATIO = 0.25

# 用于判断“疑似重复图片”的哈希距离阈值。
# 这里使用平均哈希 average hash。
# 两张图片 hash 的汉明距离小于等于该值时，认为它们高度相似。
# 数值越小越严格，越大越容易判为重复。
DUPLICATE_HASH_DISTANCE = 4

# 平均哈希尺寸。
# 8 表示生成 8x8 的 hash，也就是 64 位。
# 这是常见设置，速度快，足够用于初筛。
HASH_SIZE = 8


# ============================================================
# 4. Node A 图片类型标签
# ============================================================

# 当前本地规则版 Node A 只能稳定判断基础质量和重复。
# 这些标签用于 CSV 中的 image_type 字段。
IMAGE_TYPE_VALID = "candidate_outfit"

IMAGE_TYPE_MISSING = "missing_file"
IMAGE_TYPE_CORRUPTED = "corrupted_image"
IMAGE_TYPE_TOO_SMALL = "too_small"
IMAGE_TYPE_BAD_RATIO = "bad_aspect_ratio"
IMAGE_TYPE_DUPLICATE = "duplicate"
IMAGE_TYPE_LANDSCAPE = "landscape"
IMAGE_TYPE_UNCLEAR = "unclear"


# ============================================================
# 5. Node A 风景图本地规则阈值
# ============================================================

# 当前不调用多模态模型，也不依赖需要下载权重的人体检测模型。
# 这里只过滤“高置信度纯风景/空景候选”，避免误伤户外穿搭照。
LANDSCAPE_ANALYSIS_SIZE = 96
LANDSCAPE_NATURE_RATIO_THRESHOLD = 0.82
LANDSCAPE_BLUE_RATIO_THRESHOLD = 0.62
LANDSCAPE_GREEN_RATIO_THRESHOLD = 0.62
LANDSCAPE_MIXED_GREEN_RATIO_THRESHOLD = 0.50
LANDSCAPE_MIXED_BLUE_RATIO_THRESHOLD = 0.25
LANDSCAPE_FOREGROUND_COMPONENT_THRESHOLD = 0.08

# YOLOv8n 只用于轻量检测 person 类，避免把远景/空景送到 Node B。
ENABLE_YOLO_LANDSCAPE_FILTER = True
YOLO_MODEL_PATH = PROJECT_ROOT / "yolov8n.pt"
YOLO_PERSON_CONFIDENCE_THRESHOLD = 0.25
LANDSCAPE_PERSON_KEEP_RATIO_THRESHOLD = 0.12
LANDSCAPE_TOTAL_PERSON_KEEP_RATIO_THRESHOLD = 0.12
LANDSCAPE_GROUP_PERSON_COUNT_KEEP_THRESHOLD = 3
LANDSCAPE_SMALL_PERSON_RATIO_THRESHOLD = 0.055
LANDSCAPE_NO_PERSON_NATURE_RATIO_THRESHOLD = 0.35
LANDSCAPE_SMALL_PERSON_NATURE_RATIO_THRESHOLD = 0.35


# ============================================================
# 6. 工具函数
# ============================================================

def ensure_output_dirs() -> None:
    """
    确保所有输出目录存在。

    每个节点脚本启动时都可以调用该函数。
    exist_ok=True 表示目录已存在时不报错。
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_LABEL_DIR.mkdir(parents=True, exist_ok=True)
