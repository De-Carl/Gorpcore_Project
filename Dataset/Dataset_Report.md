# Gorpcore_Project 数据集说明报告

## 1. 项目概览

本目录整理了围绕“机能风 / Gorpcore”主题采集的多平台数据，覆盖图文笔记、视频弹幕、用户评论与电商评价等内容。整体目标是为后续的舆情分析、痛点归纳、商品对比和多模态建模提供统一的数据基础。

从数据形态上看，这份资料同时包含结构化 JSON、原始脚本、调试中间文件和图片资源，属于一个“采集脚本 + 原始数据 + 清洗后结果 + 本地图片”的完整数据工作区。

## 2. 各来源文件夹详细说明

### 2.1 `Dataset/bilibili`

该目录保存 B 站机能风相关视频的采集脚本和结果，重点是弹幕和评论文本。

- `bilibili_scraper.py`: 采集脚本，负责搜索视频、读取视频信息、抓取弹幕和高赞评论，并根据痛点关键词进行标记。
- `bilibili_results.json`: 结果文件，保存全部弹幕、全部评论、痛点样本和统计汇总。
- `说明.txt`: 子目录的简要说明。

数据结构说明：

- `summary`: 汇总统计对象，包含 `total_danmaku`、`pain_point_danmaku`、`total_comments`、`pain_point_comments`。
- `pain_point_keywords`: 痛点关键词数组，例如“太热”“太重”“不实用”“性价比”等。
- `high_like_pain_comments`: 高赞痛点评论列表，按点赞数排序后截取。
- `pain_point_danmaku`: 被标记为痛点的弹幕列表。
- `all_danmaku`: 所有弹幕记录，每条通常包含 `keyword`、`bvid`、`video_title`、`text`、`is_pain_point`。
- `all_comments`: 所有评论记录，每条通常包含 `keyword`、`bvid`、`video_title`、`text`、`like_count`、`is_pain_point`。

适合用途：

- 机能风相关话题的情绪分析和痛点挖掘。
- 视频内容与弹幕反馈的主题匹配分析。
- 高赞评论中的用户态度归纳。

### 2.2 `Dataset/jd`

该目录保存京东竞品评论采集脚本和评论结果，重点是负面或中评样本。

- `jd_review_scraper.py`: 采集脚本，按竞品关键词搜索商品并抓取评论。
- `jd_reviews.json`: 结果文件，保存结构化评论数据。

数据结构说明：

- `summary`: 汇总对象，包含 `total_reviews` 和 `by_brand`。
- `reviews`: 评论列表，每条记录是一个商品评论对象，字段包括：
	- `platform`: 固定为 `jd`。
	- `query`: 搜索词，如“始祖鸟 冲锋衣”。
	- `product_id`: 商品 ID。
	- `product_name`: 商品名称。
	- `score`: 评分，通常只保留 1-2 星，若接口未返回则可能为 0。
	- `content`: 评论正文。
	- `creation_time`: 评论时间。
	- `product_color`: 颜色信息。
	- `product_size`: 尺码信息。

适合用途：

- 竞品负面评价归因。
- 服装性能、舒适度和做工问题总结。
- 不同品牌口碑对比。

### 2.3 `Dataset/taobao`

该目录保存淘宝/天猫竞品评论采集脚本和结果，数据结构与京东部分基本一致，但来源平台不同。

- `taobao_review_scraper.py`: 采集脚本，负责搜索商品并抓取评论。
- `taobao_reviews.json`: 结果文件，保存结构化评论数据。

数据结构说明：

- `summary`: 汇总对象，包含 `total_reviews` 和 `by_brand`。
- `reviews`: 评论列表，每条记录是一个商品评论对象，字段包括：
	- `platform`: 固定为 `taobao`。
	- `query`: 搜索词，如“萨洛蒙 徒步鞋”。
	- `product_id`: 商品 ID。
	- `product_name`: 商品名称。
	- `score`: 评分，支持本地过滤差评/中评。
	- `content`: 评论正文。
	- `creation_time`: 评论时间。
	- `product_color`: 颜色信息。
	- `product_size`: 尺码信息。

适合用途：

- 电商场景下的用户抱怨与差评分析。
- 与京东评论进行跨平台对照。
- 竞品质量和价格感知研究。

### 2.4 `Dataset/xhs`

该目录保存小红书笔记采集、图片下载和调试相关内容，是当前最完整的图文数据部分。

- `xhs.py`: 核心采集脚本，负责搜索笔记、提取正文、解析发布时间、下载图片并写出结果文件。
- `xiaohongshu_auth_state.json`: 登录态缓存文件，用于保持会话。
- `xiaohongshu_with_images.json`: 核心结果文件，记录笔记文本、图片地址、发布时间和本地图片路径。
- `xiaohongshu_debug/`: 调试目录，保存搜索接口的原始 payload。
- `xiaohongshu_images/`: 本地图片仓库，按关键词和笔记 ID 分层存储图片。
- `debug_Gorpcore.png`、`debug_机能风穿搭.png`: 调试截图。
- `说明.txt`: 子目录说明。

数据结构说明：

- `xiaohongshu_with_images.json` 顶层是一个数组，每个元素是一篇笔记。
- 每条笔记记录通常包含：
	- `keyword`: 搜索关键词，例如 `#机能风穿搭`、`#Gorpcore`。
	- `note_id`: 笔记唯一 ID。
	- `note_url`: 笔记网页链接。
	- `share_url`: 可分享链接。
	- `xsec_token`: Web 访问所需的 token。
	- `can_open_in_web`: 是否可直接在网页中打开。
	- `title_text`: 标题文本。
	- `raw_text`: 正文内容。
	- `text_source`: 文本来源位置，例如详情页。
	- `image_urls`: 原始图片外链数组。
	- `downloaded_image_paths`: 已下载到本地的图片路径数组。
	- `publish_timestamp`: 原始发布时间戳。
	- `publish_time_text`: 页面展示的时间文本。
	- `publish_time_resolved`: 标准化后的发布时间字符串。

图片目录结构说明：

- 路径层级为 `xiaohongshu_images/关键词/笔记ID/图片文件`。
- 例如某条 `#机能风穿搭` 笔记会落在 `xiaohongshu_images/机能风穿搭/697b27ff000000002103cb21/` 下。
- 图片文件一般按 `image_01.webp`、`image_02.webp` 这样的顺序命名，和 `downloaded_image_paths` 一一对应。

适合用途：

- 图文联合分析。
- 机能风穿搭图片风格识别。
- 以笔记为单位的内容审阅、分类和多模态建模。

## 3. 数据来源与采集逻辑

### 3.1 小红书：图文笔记数据

小红书部分围绕 `#机能风穿搭` 和 `#Gorpcore` 两个关键词采集笔记。脚本会提取笔记正文、标题、发布时间、图片外链，并将图片下载到本地目录中。最终形成一个可同时用于文本分析与图像分析的数据集。

### 3.2 B 站：弹幕和评论数据

B 站部分面向机能风评测视频，抓取视频弹幕和高赞评论，并额外根据预设的“痛点关键词”识别负面或问题导向表达，例如“太热”“太重”“不实用”“性价比”等。

### 3.3 京东与淘宝：竞品负面评价数据

京东和淘宝部分均围绕竞品品牌与品类关键词采集商品评论，并在本地只保留差评或中评，形成更偏向“用户抱怨/痛点”的评价样本。典型查询包括：

- 始祖鸟 冲锋衣
- 始祖鸟 软壳
- 萨洛蒙 冲锋衣
- 萨洛蒙 徒步鞋
- 巴塔哥尼亚 冲锋衣
- 始祖鸟 抓绒

## 4. 数据特征总结

- 多平台覆盖：包含小红书、B 站、京东和淘宝四类来源。
- 多模态特征：同时有文本、图片和视频相关衍生文本。
- 任务导向明确：数据采集目标围绕机能风 / Gorpcore，并且包含大量与“痛点”相关的负面样本。
- 便于后续分析：JSON 文件字段较完整，适合直接用 Python 读取和二次处理。

## 5. 推荐使用方式

1. 文本分析：读取各平台 JSON 中的正文、评论或弹幕字段，做主题建模、情感分析、关键词统计。
2. 图像分析：使用 `Dataset/xhs/xiaohongshu_with_images.json` 中的 `downloaded_image_paths` 读取本地图片，进行视觉分类或图文联合分析。
3. 痛点挖掘：优先分析 B 站、京东和淘宝中的负面表达，提取用户对机能风产品的典型不满。
4. 竞品对比：结合京东和淘宝评论，比较不同品牌在舒适度、实用性、价格和做工方面的反馈。

## 6. 结论

该文件夹已经形成一套较完整的机能风数据采集资产：小红书提供图文内容，B 站提供视频互动反馈，京东和淘宝提供竞品负面评价。整体上，这是一套适合做“机能风 / Gorpcore 主题内容分析 + 用户痛点分析 + 多模态研究”的基础数据集。