# Evidence Fusion Visual Displays 小报告

## 1. 目录目标

`Evidence_fusion_visual_dispalys/` 目标是把现有项目中的图片证据、文本证据和 Dataset 元数据融合起来，形成一个可分析的结构化特征数据库，并生成 early insights 可视化图表。

本目录不重新爬取数据，也不调用外部视觉大模型。它只读取项目中已经存在的 Node A/B/C/D 输出，并将所有新增结果写入：

```text
Evidence_fusion_visual_dispalys/output/
```

## 2. 输入数据

主程序为：

```text
Evidence_fusion_visual_dispalys/member_e_feature_builder.py
```

它读取的核心输入包括：

| 输入文件 | 作用 |
|---|---|
| `Gorpcore_Agent/output/image_index.csv` | 图片级索引，提供 `Image_ID`、`note_id`、图片相对路径和文本上下文 |
| `Gorpcore_Agent/output/quality_filtered_images.csv` | Node A 图片质量筛选结果，只保留 `passed=True` 的图片 |
| `Gorpcore_Agent/output/json_labels/` | Node B 视觉标签 JSON，当前覆盖量较少 |
| `Gorpcore_Agent/text_analysis/output/text_analysis/text_feature_vectors.csv` | 文本关键词、痛点、情感、颜色词、材料词、功能词、场景词 |
| `Gorpcore_Agent/text_analysis/output/text_analysis/pain_point_table.csv` | 痛点明细表 |
| `Gorpcore_Agent/text_analysis/output/text_analysis/word_frequency.csv` | 词频表，用于词云展示 |

本次运行统计为：

- 图片索引记录：1077 条
- 通过 Node A 筛选图片：946 张
- 文本特征记录：39602 条
- 痛点记录：120 条
- 成功颜色提取：946 张
- 文本特征匹配图片：497 张

## 3. 证据融合流程

融合过程以 `Image_ID` 为图片级主键，以 `Source_ID` 为笔记级文本主键。

图片 ID 形式为：

```text
GRP-XHS-{note_id}-{image_index}
```

文本 Source ID 形式为：

```text
GRP-XHS-{note_id}
```

因此程序通过去掉图片 ID 末尾的图片序号构造文本连接键：

```text
Source_ID = Image_ID without the final image index
```

融合逻辑可以表示为：

```text
Feature_DB = Image_Index ⋈ Quality_Filter ⋈ Color_Features ⋈ Component_Summary ⋈ Text_Features
```

其中 `⋈` 表示按 `Image_ID` 或 `Source_ID` 进行连接。

## 4. 颜色特征提取算法

颜色特征来自本地图片处理，不依赖大模型。每张图片先缩放到较小尺寸，然后将像素表示为 RGB 向量：

```text
x_i = [R_i, G_i, B_i], i = 1, 2, ..., N
```

程序使用 MiniBatch K-Means 将像素聚成最多 5 个颜色簇。目标函数为：

```text
minimize Σ(i=1 to N) ||x_i - μ_{c_i}||^2
```

其中：

- `x_i` 是第 `i` 个像素的 RGB 向量
- `μ_{c_i}` 是该像素所属颜色簇的中心
- `c_i` 是像素所属簇编号

每个颜色簇的占比为：

```text
r_k = n_k / N
```

其中：

- `n_k` 是第 `k` 个颜色簇的像素数
- `N` 是总采样像素数

程序按 `r_k` 从大到小排序：

```text
Primary_Color = argmax_k r_k
Secondary_Color = second_argmax_k r_k
```

再将 RGB 转换为 HEX：

```text
HEX = #{R_hex}{G_hex}{B_hex}
```

最后根据 HSV 色相、饱和度和亮度，把主色映射到颜色家族：

```text
black, white, gray, olive_or_green, khaki_or_beige, brown, blue, red_or_orange, yellow, purple
```

输出文件：

```text
output/color_features.csv
```

主要字段包括：

- `Image_ID`
- `Primary_HEX`
- `Secondary_HEX`
- `Dominant_Color_Name`
- `Color_Family`
- `Primary_Color_Ratio`
- `Secondary_Color_Ratio`
- `Color_Extraction_Status`

## 5. 服装组件证据汇总

组件检测没有伪造全量视觉识别结果，而是采用“证据分层”策略：

```text
Component_Source =
    node_b, if visual label exists
    text_heuristic, if text evidence exists
    unknown, otherwise
```

当前 Node B 视觉标签覆盖较少，因此本次 946 张图片中：

- `text_heuristic`：198 条
- `unknown`：748 条

文本启发式规则主要检查标题、正文和文本分析字段中是否出现组件关键词：

| 组件字段 | 文本证据示例 |
|---|---|
| `Drawcord` | 抽绳、束带、drawstring |
| `Buckle` | 卡扣、扣具、buckle |
| `Reflective` | 反光、reflective |
| `Hood` | 帽子、连帽、hood |

组件置信度定义为：

```text
confidence =
    Node_B_Confidence, if source = node_b
    0.4, if source = text_heuristic
    0.0, if source = unknown
```

输出文件：

```text
output/component_summary.csv
```

主要字段包括：

- `Pockets`
- `Zipper_Type`
- `Drawcord`
- `Buckle`
- `Reflective`
- `Hood`
- `Fit`
- `Scenario`
- `Visual_Weight`
- `Component_Source`
- `Component_Confidence`

## 6. 融合特征数据库

最终主表为：

```text
output/feature_database.csv
```

它一行对应一张通过 Node A 筛选的图片，共 946 行。该表把图片元数据、颜色特征、组件证据和文本分析结果合并到一起。

核心字段包括：

- 图片身份：`Image_ID`、`note_id`、`Source_ID`
- 文本上下文：`keyword`、`title_text`、`raw_text`
- 图片路径：`image_path`
- 颜色字段：`Primary_HEX`、`Secondary_HEX`、`Color_Family`
- 组件字段：`Pockets`、`Zipper_Type`、`Hood`、`Reflective`
- 文本字段：`Text_Keywords`、`Text_Pain_Points`、`Text_Sentiment`
- 质量字段：`Component_Source`、`Component_Confidence`、`Color_Extraction_Status`

## 7. 可视化图表说明

本目录生成 6 张阶段性图表：

| 图表 | 输出文件 | 数据来源 |
|---|---|---|
| 颜色分布图 | `fig_color_distribution.png` | `color_features.csv` |
| 场景分布图 | `fig_scene_distribution.png` | `feature_database.csv` |
| 版型分布图 | `fig_fit_distribution.png` | `feature_database.csv` |
| 痛点分布图 | `fig_painpoint_distribution.png` | `pain_point_table.csv` |
| 视觉重量与痛点关系图 | `fig_visual_weight_painpoint.png` | `feature_database.csv` |
| Visual Word Cloud demo | `fig_visual_wordcloud.png` | `word_frequency.csv` 和文本特征字段 |

### 7.1 分布图统计公式

对于任意类别变量 `y`，例如颜色家族、场景、版型或痛点，类别 `a` 的计数为：

```text
count(a) = Σ(i=1 to n) I(y_i = a)
```

其中 `I(condition)` 是指示函数：

```text
I(condition) = 1, if condition is true
I(condition) = 0, otherwise
```

类别占比可以表示为：

```text
p(a) = count(a) / n
```

### 7.2 视觉重量与痛点关系

视觉重量与痛点关系图使用交叉表。对于视觉重量 `w` 和痛点 `p`，统计值为：

```text
C(w, p) = Σ(i=1 to n) I(Visual_Weight_i = w and Pain_Point_i = p)
```

由于当前全量图片缺少可靠的视觉重量标签，该图属于 early-insight/demo，不应解读为最终统计结论。

### 7.3 词云权重

词云根据词频表和文本特征字段生成。词 `t` 的基础权重为：

```text
weight(t) = frequency(t)
```

对于领域字段中的关键词，程序会给予额外权重增强：

```text
weight'(t) = max(frequency(t), 5 * domain_count(t))
```

这样可以让材料、功能、场景等与设计分析更相关的词在词云中更明显。

## 8. 输出文件清单

当前输出目录为：

```text
Evidence_fusion_visual_dispalys/output/
```

文件清单：

```text
color_features.csv
component_summary.csv
feature_database.csv
member_e_summary.json
fig_color_distribution.png
fig_scene_distribution.png
fig_fit_distribution.png
fig_painpoint_distribution.png
fig_visual_weight_painpoint.png
fig_visual_wordcloud.png
```

其中 `member_e_summary.json` 记录了本次运行的输入文件、输入数量、输出数量、颜色提取状态、组件证据来源和局限说明。

## 9. 局限性

1. 当前 Node B 视觉标签只有少量 JSON 文件，因此本目录不声称完成了全量服装组件视觉检测。
2. 大多数组件字段来自文本启发式或保持 `unknown`，适合作为证据汇总，不适合作为最终人工标注结果。
3. 颜色特征基于整张图片的像素聚类，因此背景颜色可能影响主色判断。
4. 视觉重量与痛点关系图受视觉标签覆盖量限制，只能作为阶段性展示。
5. 本目录输出路径已经统一为项目相对路径，便于提交和复现实验。

## 10. 运行方式

在项目根目录运行：

```bash
python Evidence_fusion_visual_dispalys/member_e_feature_builder.py
```

运行成功后，所有结果会写入：

```text
Evidence_fusion_visual_dispalys/output/
```
