# Presentation Asset Summary

## One-Sentence Project Explanation

This project is a data-management and multimodal curation system for Gorpcore trend intelligence: it collects text and images from multiple public platforms, then uses rule-based filtering, visual annotation, semantic cross-checking and human review to convert noisy raw data into structured evidence for design decisions.

## Data Source Table

| Source | Records | Role |
|---|---:|---|
| Bilibili danmaku | 33,886 | video interaction text |
| Bilibili comments | 5,044 | high-like discussion and pain points |
| Taobao reviews | 481 | e-commerce feedback |
| JD reviews | 0 | attempted e-commerce source |
| Xiaohongshu notes | 200 | social notes with image metadata |
| Xiaohongshu images | 1,077 | local multimodal image corpus |

## Key Metrics

| Metric | Value |
|---|---:|
| Raw text records analysed | 39,602 |
| Pain-point records | 120 |
| Indexed XHS images | 1,077 |
| Node A quality pass | 930 |
| Node B annotated images | 924 |
| Final curated images | 709 |
| Average final confidence | 0.896 |

## Presentation-Ready Design Insights

| Angle | Finding | Evidence count |
|---|---|---:|
| Main visual form | Full-body outfit dominates | 459 |
| Main scenario | Urban_Commute dominates | 513 |
| Main colour signal | Black / white / gray are leading neutral colours | 510 |
| Main consumer pain point | High price | 68 |
| Method warning | Sentiment is mostly neutral, so ontology-based pain-point extraction matters | 36,563 |

## Scope Notes

- The final presentation should prioritize `Gorpcore_Agent/output/final_curated_records.csv` and node logs. The final curated image count is 709.
- `Evidence_fusion_visual_dispalys/output/member_e_summary.json` is a Member E evidence-fusion module snapshot. Its 946 rows explain colour extraction and feature-fusion coverage, and should not be mixed with the final human-reviewed count.

## Suggested Presentation Logic

1. Do not present this as a simple scraping project. Emphasize the data-curation pipeline.
2. Start with the business problem: hardcore outdoor apparel can feel too hot, heavy, expensive and over-designed for urban commuting.
3. Then explain the method: multi-source collection, pain-point ontology, image quality gatekeeping, visual annotation, semantic review and human audit.
4. End with the result: 709 final curated image records and evidence-backed signals on colour, scenario, visual weight and consumer pain points.

## Generated Figures

- `01_multisource_corpus.png`
- `02_curation_pipeline_funnel.png`
- `03_visual_taxonomy.png`
- `04_color_palette.png`
- `05_painpoints_sentiment.png`
- `06_evidence_fusion_coverage.png`
- `07_visual_evidence_board.png`
