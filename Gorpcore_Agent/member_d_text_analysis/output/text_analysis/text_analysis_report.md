# Node D 文本分析报告

## 数据概览

- **输入数据来源**：C:\Users\pc\Gorpcore_Project\Dataset\xhs\xiaohongshu_with_images.json | C:\Users\pc\Gorpcore_Project\Dataset\taobao\taobao_reviews.json | C:\Users\pc\Gorpcore_Project\Dataset\bilibili\bilibili_results.json
- **输入总条数**：39611
- **有效分析条数**：39602

## 各平台文本数量

### 输入阶段

- bilibili: 38930
- taobao: 481
- xiaohongshu: 200

### 有效分析阶段

- bilibili: 38921
- taobao: 481
- xiaohongshu: 200

## Top 20 高频词

1. 5 (6814)
2. 的 (5689)
3. 了 (4482)
4. 我 (2473)
5. 1 (2269)
6. 是 (2094)
7. 4 (1499)
8. 啊 (1284)
9. 2 (1197)
10. 3 (1084)
11. 不 (1050)
12. 哈哈哈 (1006)
13. 都 (972)
14. 好 (950)
15. 有 (939)
16. 穿 (935)
17. 这个 (924)
18. 也 (854)
19. 评价 (840)
20. 你 (838)

## 各痛点数量

- 价格高: 68
- 不透气: 29
- 不适合通勤: 8
- 不耐磨: 5
- 太重: 5
- 版型差: 4
- 拉链问题: 1

## 情感分布

- positive: 2698 (6.8%)
- neutral: 36563 (92.3%)
- negative: 341 (0.9%)

## 输出文件列表

- `cleaned_text.csv`
- `tokenized_text.csv`
- `word_frequency.csv`
- `text_feature_vectors.csv`
- `pain_point_table.csv`
- `sentiment_labels.csv`
- `micro_ontology.json`
- `painpoint_design_mapping.csv`
- `text_analysis_report.md`
