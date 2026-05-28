"""
Dataset v0 加载与图片级索引构建工具。

当前 xiaohongshu_with_images.json 是“笔记级”数据：
一条记录对应一篇小红书笔记，一篇笔记可能包含多张图片。

但是后续 Node A / Node B / Node C 的处理单位应该是“单张图片”，
所以本文件的核心任务是：

1. 读取 Dataset/xhs/xiaohongshu_with_images.json
2. 遍历每条笔记中的 downloaded_image_paths
3. 将笔记级数据展开成图片级 records
4. 为每张图片生成唯一 Image_ID
5. 保留图片对应的文本、note_id、发布时间等上下文信息

图片级数据示例：

{
    "Image_ID": "GRP-XHS-686b887200000000120334f2-01",
    "note_id": "686b887200000000120334f2",
    "keyword": "#机能风穿搭",
    "title_text": "...",
    "raw_text": "...",
    "publish_time_resolved": "2025-07-07",
    "relative_image_path": "xiaohongshu_images\\机能风穿搭\\...\\image_01.jpg",
    "image_path": "E:\\code\\Project\\Dataset\\xhs\\xiaohongshu_images\\机能风穿搭\\...\\image_01.webp"
}

注意：
这里不做图片质量判断，只负责“把数据读对、路径拼对、ID 生成稳定”。
"""


import csv
import json
from pathlib import Path
from typing import List, Dict, Any
from config import IMAGE_BASE_DIR, IMAGE_INDEX_CSV, RAW_DATA_JSON, ensure_output_dirs

def load_raw_dataset(raw_json_path: Path=RAW_DATA_JSON) -> List[Dict[str, Any]]:
    """
    读取原始 Dataset v0 JSON 文件。

    参数:
        raw_json_path:
            原始 JSON 文件路径，默认读取 config.py 中配置的 RAW_DATA_JSON。

    返回:
        List[Dict[str, Any]]:
            小红书笔记级数据列表。

    异常:
        FileNotFoundError:
            当 JSON 文件不存在时抛出，提示用户检查数据集路径。
        json.JSONDecodeError:
            当 JSON 格式不合法时抛出，说明原始数据可能损坏。
    """
    if not raw_json_path.exists():
        raise FileNotFoundError(f"原始数据文件未找到: {raw_json_path}\n请检查数据集路径是否正确，确保 {raw_json_path} 存在。")
    
    with raw_json_path.open("r",encoding="utf-8") as f:
        data=json.load(f)

    if not isinstance(data, list):
        raise ValueError("原始数据格式异常：顶层结构应为 list。")
    
    return data

def normalize_relative_image_path(relative_path: str) -> Path:
    """
    规范化 JSON 中保存的相对图片路径。

    原始 JSON 中的 downloaded_image_paths 可能是 Windows 风格：
        xiaohongshu_images\\机能风穿搭\\xxx\\image_01.jpg

    也可能在其他环境中变成：
        xiaohongshu_images/机能风穿搭/xxx/image_01.jpg

    这里统一交给 pathlib.Path 处理，并去掉路径中可能存在的多余空白。

    参数:
        relative_path:
            JSON 中的相对图片路径字符串。

    返回:
        Path:
            规范化后的相对路径对象。
    """
    return Path(relative_path.strip())

def resolve_image_path(relative_path: str) -> Path:
    """
    根据 JSON 中的相对路径，解析出图片的真实绝对路径。

    当前项目的数据集目录层级：

    Dataset/
      xhs/
        xiaohongshu_with_images.json
        xiaohongshu_images/
          Gorpcore/
          机能风穿搭/

    而 JSON 中的路径通常从 xiaohongshu_images 开始，例如：
        xiaohongshu_images\\机能风穿搭\\note_id\\image_01.jpg

    因此完整路径应当是：
        IMAGE_BASE_DIR / relative_path

    也就是：
        Dataset/xhs/xiaohongshu_images/机能风穿搭/...

    参数:
        relative_path:
            JSON 中记录的相对图片路径。

    返回:
        Path:
            图片绝对路径。
    """
    normalized = normalize_relative_image_path(relative_path)
    return (IMAGE_BASE_DIR / normalized).resolve() # resolve() 获取绝对路径，避免后续路径操作出错

def build_image_id(note_id: str, image_index: int) -> str:
    """
    为每张图片生成稳定的唯一 Image_ID。 

    命名规则：
        GRP-XHS-{note_id}-{两位图片序号}

    示例：
        GRP-XHS-686b887200000000120334f2-01

    这样做的好处：
    1. GRP 表示 Gorpcore Project
    2. XHS 表示数据来源是小红书
    3. note_id 可以追溯到原始笔记
    4. 图片序号可以区分同一笔记下的多张图

    参数:
        note_id:
            小红书笔记 ID。
        image_index:
            图片在当前笔记中的序号，从 1 开始。

    返回:
        str:
            唯一图片 ID。
    """
    return f"GRP-XHS-{note_id}-{image_index:02d}"


def safe_text(value: Any) -> str:
    """
    将 JSON 中可能为 None 的文本字段规范化为空字符串。
    """
    if value is None:
        return ""

    return str(value).strip()


def build_image_records(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将笔记级数据展开成图片级数据。

    参数:
        raw_data:
            从 xiaohongshu_with_images.json 读取出的笔记级数据列表。

    返回:
        List[Dict[str, Any]]:
            图片级 records 列表，每条记录对应一张图片。
    """
    image_record: List[Dict[str, Any]] = [] # :代表类型提示，说明 image_record 是一个列表，列表中的元素是字典，字典的键是字符串，值可以是任意类型。

    for note in raw_data:
        note_id = safe_text(note.get("note_id", "")) # 笔记 ID，转换为字符串并去除空白
        # 如果 note_id 缺失，说明这条数据无法稳定追溯。
        # 这里仍然保留，但用 unknown_note 兜底，避免程序中断。
        if not note_id:
            note_id = "unknown_note"

        download_paths=note.get("downloaded_image_paths", [])
        # 如果 downloaded_image_paths 不是列表，说明数据格式异常。
        # 这里跳过该条，避免影响整体 pipeline。

        if not isinstance(download_paths, list):
            continue

        for index, relative_path in enumerate(download_paths, start=1):
            if not relative_path:
                continue

            image_id = build_image_id(note_id, index) # 生成图片 ID
            absolute_image_path = resolve_image_path(str(relative_path)) # 解析图片绝对路径

            # 将笔记上下文复制到图片级记录中。
            # 后续 Node C 做语义交叉检查时，需要 raw_text/title_text。
            image_record.append(
                {
                    "Image_ID": image_id,
                    "note_id": note_id,
                    "keyword": safe_text(note.get("keyword", "")),
                    "note_url": safe_text(note.get("note_url", "")),
                    "title_text": safe_text(note.get("title_text", "")),
                    "raw_text": safe_text(note.get("raw_text", "")),
                    "text_source": safe_text(note.get("text_source", "")),
                    "publish_timestamp": safe_text(note.get("publish_timestamp", "")),
                    "publish_time_text": safe_text(note.get("publish_time_text", "")),
                    "publish_time_resolved": safe_text(note.get("publish_time_resolved", "")),
                    "relative_image_path": safe_text(relative_path),
                    "image_path": str(absolute_image_path),
                }
            )

    return image_record

def save_image_index_csv(image_records: List[Dict[str, Any]], output_path: Path=IMAGE_INDEX_CSV) -> None:
    """
    将图片级索引保存为 CSV。

    这个 CSV 主要用于人工检查和调试：
    可以快速确认图片路径是否正确、Image_ID 是否稳定生成。

    参数:
        image_records:
            图片级记录列表。
        output_path:
            输出 CSV 路径。
    """   
    ensure_output_dirs()
    if not image_records:
        raise ValueError("image_records 为空，无法保存 CSV。请检查数据加载和处理逻辑。")
    
    fieldnames = [
        "Image_ID",
        "note_id",
        "keyword",
        "note_url",
        "title_text",
        "raw_text",
        "text_source",
        "publish_time_resolved",
        "relative_image_path",
        "image_path"
    ]

    with output_path.open("w",encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f,fieldnames=fieldnames)
        writer.writeheader()

        for record in image_records:
            writer.writerow({key: record.get(key, "") for key in fieldnames})

def load_image_records(save_index: bool=False) -> List[Dict[str, Any]]:
    """
    对外提供的主函数：读取原始数据并返回图片级 records。

    参数:
        save_index:
            是否顺便保存 image_index.csv。
            调试阶段建议设为 True。

    返回:
        List[Dict[str, Any]]:
            图片级 records。
    """
        
    raw_data = load_raw_dataset()       
    image_records = build_image_records(raw_data)

    if save_index:
        save_image_index_csv(image_records)

    return image_records


if __name__ == "__main__":
    """
    允许单独运行本文件进行检查：

        python dataset_loader.py

    运行后会：
    1. 读取原始 JSON
    2. 展开图片级 records
    3. 保存 output/image_index.csv
    4. 打印图片总数
    """
    records = load_image_records(save_index=True)
    print(f"图片级记录构建完成，共 {len(records)} 张图片。")
    print(f"图片索引已保存到: {IMAGE_INDEX_CSV}")
