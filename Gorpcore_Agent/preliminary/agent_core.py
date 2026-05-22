import os
import base64
import json
from openai import OpenAI

# 1. 初始化客户端 (使用阿里云百炼的兼容接口)
API_KEY = "sk-63ae7a96ebb44bf99b4498256140703c"  

client = OpenAI(
    api_key=API_KEY, 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 2. 图片转 Base64 的编码函数
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_clothing_image(image_path):
    print(f"Reading and encoding image: {image_path} ...")
    base64_image = encode_image(image_path)
    
    # 3.严格的 System Prompt 
    system_prompt = """
    You are a professional fashion data analyst and clothing curation expert.
    Please analyze the user-provided Gorpcore outfit image.
    You must return strictly valid JSON only, without any Markdown markers,
    code block wrappers (such as ```json), or explanatory text.

    Required JSON fields:
    {
        "primary_color": "string, the dominant clothing color (e.g., olive green, black, bright yellow)",
        "has_waterproof_zipper": "boolean (true/false), whether a waterproof zipper design is clearly visible",
        "pockets_count": "integer, approximate number of visible three-dimensional pockets",
        "style_keywords": "array, extract 2-3 keywords about material or style (e.g., ['matte', 'technical', 'oversized'])"
    }
    """

    print("Requesting multimodal visual extraction with Qwen-VL-Max. Please wait...")
    
    try:
        # 4. 发起 API 请求
        response = client.chat.completions.create(
            model="qwen-vl-max",  # qwen-vl-max 是目前阿里最强的视觉模型
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]}
            ], # messages 中直接嵌入 Base64 图片数据，阿里云的兼容接口支持这种方式
            response_format={"type": "json_object"}  # 强制大模型以 JSON 格式吐出数据
        )

        # 5. 获取并解析结果
        raw_result = response.choices[0].message.content
        parsed_json = json.loads(raw_result) # 验证是否为合法 JSON
        
        print("\nAI extraction completed! Structured data:")
        print(json.dumps(parsed_json, indent=4, ensure_ascii=False))
        
        return parsed_json

    except Exception as e:
        print(f"\nError occurred: {e}")
        return None

# 执行测试
if __name__ == "__main__":
    target_image = "test.jpg"
    if os.path.exists(target_image):
        analyze_clothing_image(target_image)
    else:
        print(f"Image {target_image} not found. Please make sure it is in the same directory as the script.")