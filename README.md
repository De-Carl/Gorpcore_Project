# Gorpcore Trend Intelligence — A Multimodal Data Curation Pipeline

> INFO 202 *Data Curation* group project. From raw, noisy, multi-platform consumer
> data to a curated multimodal corpus, and from that corpus to an actionable
> design direction for the **"Lightweight Gorpcore"** urban-outdoor season.

This repository documents the full lifecycle of a data-curation project: how raw
social and e-commerce data was **collected**, **filtered**, **annotated**,
**cross-checked**, **human-reviewed**, **fused**, and finally **communicated** as
a design brief and an interactive website.

The guiding principle throughout is **honest, auditable curation**: every figure
on the website and in this document traces back to a file in this repository, and
the known limitations of the dataset are stated explicitly rather than hidden.

---

## 1. The problem

"Gorpcore" (technical mountain/outdoor gear worn as everyday fashion) is trending,
but social media is full of *idealised* posts that do not reflect what consumers
actually want or complain about. The project goal is to:

1. Collect consumer signal about gorpcore across multiple Chinese platforms.
2. Curate it into a trustworthy multimodal dataset (images + text), discarding
   noise, screenshots, landscapes, marketing, and duplicates.
3. Turn the curated corpus into a concrete design direction — colour, material,
   silhouette, and functional details — for an athletic-apparel design team.

---

## 2. Repository structure

```
Gorpcore_Project/
├── Dataset/                         # Stage 1 — raw data collection (Dataset v0)
│   ├── xhs/                         #   Xiaohongshu notes + downloaded images
│   ├── bilibili/                    #   Bilibili danmaku + comments
│   ├── taobao/                      #   Taobao product reviews
│   ├── jd/                          #   JD reviews (collection was blocked)
│   ├── D0_visualization.py          #   Raw-data overview plots
│   └── Dataset_Report.md            #   Raw-data documentation (zh)
│
├── Gorpcore_Agent/                  # Stage 2 — the 4-node curation agent
│   ├── config.py                    #   Central paths + quality thresholds
│   ├── data_loader.py               #   Note-level JSON → image-level records
│   ├── node_a_quality_gatekeeper.py #   Node A: quality gate
│   ├── node_b_vision_annotator.py   #   Node B: vision-LLM annotation
│   ├── node_c_semantic_cross_checker.py  # Node C: image↔text cross-check
│   ├── node_d_human_reviewer.py     #   Node D: human-review consolidation
│   ├── complete_human_review.py     #   Auditable, scripted review decisions
│   ├── text_analysis/               #   Text feature + pain-point extraction
│   ├── visualize_agent_outputs.py   #   Agent-stage diagnostic plots
│   └── output/                      #   Curated records, labels, logs, sheets
│
├── Evidence_fusion_visual_dispalys/ # Stage 3 — evidence fusion + figures
│   ├── member_e_feature_builder.py  #   Joins image + text features
│   └── output/                      #   feature_database.csv + 6 figures
│
├── website/                         # Stage 4 — the trend-intelligence website
│   ├── src/                         #   React + Vite + TypeScript + Tailwind
│   ├── public/evidence/             #   9 real curated outfit images + records
│   ├── public/charts/               #   The 6 real analysis figures
│   └── dist/                        #   Production build
│
├── Project_Documents/               # Course material + assignment briefs
└── zuoyeyaoqiu/                     # Assignment requirements + project plan
```

---

## 3. The data (Dataset v0)

Raw consumer signal was collected from **four platforms**. Volumes are dominated
by Bilibili; JD collection was blocked by anti-scraping measures and contributes
no usable records — this is documented rather than papered over.

| Platform     | Content collected            | Records  | Notes                          |
| ------------ | ---------------------------- | -------- | ------------------------------ |
| Bilibili     | Danmaku (33,886) + comments (5,044) | ~38,930 | Largest text source            |
| Xiaohongshu  | Notes (200) + images (1,077) | 200 notes | Primary **image** source        |
| Taobao       | Product reviews              | 481      | Competitor review signal        |
| JD           | Product reviews              | 0        | **Collection blocked**          |
| **Total text** |                            | **~39,602** | Feeds text-feature extraction  |

---

## 4. The curation agent (4 nodes)

The core of the project is a four-node curation pipeline. Each node has a single
responsibility, writes its own CSV/JSON outputs, and logs what it did, so the
whole pipeline is **auditable end to end**.

```
   Dataset v0 (notes + images)
            │
   data_loader.py  ──►  image-level records (Image_ID = GRP-XHS-{note_id}-{idx})
            │
   ┌────────▼─────────┐
   │ Node A           │  Quality gatekeeper — local, rule-based.
   │ Quality Gate     │  Drops missing/corrupt files, too-small images,
   │                  │  bad aspect ratios, near-duplicates (avg-hash), and
   │                  │  high-confidence landscapes (color rules + YOLOv8n person check).
   └────────┬─────────┘  → quality_filtered_images.csv  (1,077 → 946 passed)
            │
   ┌────────▼─────────┐
   │ Node B           │  Vision-LLM annotator — calls Qwen-VL-Max to emit a
   │ Vision Annotator │  structured JSON label per image (category, body
   │                  │  coverage, pockets, zipper, fit, reflective, colour…).
   └────────┬─────────┘  → output/json_labels/{Image_ID}.json
            │
   ┌────────▼─────────┐
   │ Node C           │  Semantic cross-check — joins Node B labels with the
   │ Cross-checker    │  source text + text-analysis features; lowers confidence
   │                  │  or routes disagreements to the review pool.
   └────────┬─────────┘  → cross_checked_records.csv, review_pool.csv
            │
   ┌────────▼─────────┐
   │ Node D           │  Human-review consolidation — applies auditable manual
   │ Human Reviewer   │  decisions (accept / revise / reject / pending) and
   │                  │  produces the final curated record set.
   └────────┬─────────┘  → final_curated_records.csv, human_review_log.json
            │
            ▼
     Curated corpus
```

### Honest note on Node B coverage

Node B requires a paid multimodal API (Qwen-VL-Max). In the current run only
**3 image-level vision labels** were produced as a working sample. The pipeline is
fully wired to scale, but we **do not claim** full image-level component detection
across all 946 images. Downstream stages therefore fall back to **text heuristics**
or leave fields **unknown**, and this is labelled as such everywhere (see the
website's per-record provenance tags).

---

## 5. Evidence fusion (Stage 3)

`Evidence_fusion_visual_dispalys/member_e_feature_builder.py` joins the curated
image features with the text features to build a single
**`feature_database.csv`** (946 rows), then renders the analysis figures.

Key real figures (`member_e_summary.json`):

| Quantity                         | Value   |
| -------------------------------- | ------- |
| Images entering quality gate     | 1,077   |
| Images passing the gate          | **946** |
| Node B vision labels available   | 3       |
| Text feature rows                | 39,602  |
| De-duplicated pain points (n)    | 120     |
| Images cross-linked to text      | **497** |
| Component source: text heuristic | 198     |
| Component source: unknown        | 748     |

Per-image colour is extracted with **MiniBatch K-Means** (dominant + secondary
HEX, mapped to a colour family). Figures rendered into
`Evidence_fusion_visual_dispalys/output/`:

`fig_color_distribution.png`, `fig_scene_distribution.png`,
`fig_fit_distribution.png`, `fig_painpoint_distribution.png`,
`fig_visual_weight_painpoint.png`, `fig_visual_wordcloud.png`.

**Bonus — image word cloud.** `build_image_wordcloud.py` renders
`fig_image_wordcloud.png`: instead of a text cloud, it tiles 604 of the real
curated outfit photos into a mountain silhouette, ordered by colour family — the
corpus drawn with itself (course bonus item #2). It is embedded on the website as
Fig. 04.

### Pain points (de-duplicated, n = 120)

| Pain point        | Mentions |
| ----------------- | -------- |
| High price        | 68       |
| Not breathable    | 29       |
| Not commute-friendly | 8     |
| Not durable       | 5        |
| Too heavy         | 5        |
| Poor fit / silhouette | 4    |
| Zipper issues     | 1        |

These counts drive the "what consumers reject → what to design instead" panel on
the website, and the design recommendations (lightweight breathable core,
value-engineered materials, commute-ready silhouettes).

---

## 6. The website (Stage 4)

An interactive, single-page trend-intelligence brief built for an athletic-apparel
design team.

- **Stack:** React 18 · Vite 5 · TypeScript · Tailwind CSS · Framer Motion · GSAP/ScrollTrigger · Recharts.
- **Real data only:** the evidence gallery shows 9 real curated Xiaohongshu
  images (of 946) with their machine-extracted HEX swatches and a provenance tag
  (vision label / text heuristic / colour only); the trend atlas embeds the real
  word cloud; the trend-signals section uses the real pain-point counts and the
  real four-platform mix; the stat tiles report the real corpus numbers.

### Run it

**Prerequisite:** Node.js ≥ 18 (includes `npm`). Check with `node -v`. If you
don't have it, install from <https://nodejs.org> (LTS).

**Step 1 — install dependencies (first time only):**

```bash
cd website
npm install
```

**Step 2 — start the dev server (this is "launching the website"):**

```bash
npm run dev
```

Vite prints a local URL — open it in your browser (default
**<http://localhost:5173>**). The page hot-reloads as you edit. Press `Ctrl+C`
in the terminal to stop it.

**Optional — build & preview the production version:**

```bash
npm run build     # type-checks + bundles into website/dist
npm run preview   # serves the built site (default http://localhost:4173)
```

The build copies `public/evidence/` and `public/charts/` into `dist/`, so the
images and figures are self-contained — `dist/` can be deployed to any static host.

---

## 7. Running the curation pipeline

All paths and thresholds are centralised in `Gorpcore_Agent/config.py`
(`PROJECT_ROOT` is derived from the file location, so the repo is portable).

**Recommended — the orchestrator** chains the whole Agent end to end
(**collect → validate → record → label**), stops on the first node failure,
writes `output/pipeline_run_log.json`, and pauses at the human-review gate so a
person owns the final decision (course bonus item #1):

```bash
cd Gorpcore_Agent
python run_pipeline.py                 # use existing Dataset v0; pause for manual review
python run_pipeline.py --collect       # ALSO run the scrapers first (browser + login)
python run_pipeline.py --auto-review   # apply the scripted, auditable review decisions
python run_pipeline.py --skip-vision   # skip Node B if you have no Qwen-VL-Max API key
python run_pipeline.py --limit 20      # annotate only the first 20 images in Node B
python run_pipeline.py --fuse          # also run evidence fusion + figures at the end
```

Collection (`--collect`) is opt-in: the scrapers drive a real browser via
Playwright and need a logged-in session, so it is human-supervised and one
platform failing (e.g. JD's anti-scraping) does not abort the others. Without
the flag the pipeline reuses the committed Dataset v0 — the normal reproducible
path.

**Or run each node on its own** (each script is still independently runnable):

```bash
cd Gorpcore_Agent
python data_loader.py                 # build image-level index
python node_a_quality_gatekeeper.py   # quality gate  → quality_filtered_images.csv
python node_b_vision_annotator.py     # vision labels (requires Qwen-VL-Max API key)
python node_c_semantic_cross_checker.py
python node_d_human_reviewer.py       # consolidate human review
python visualize_agent_outputs.py     # diagnostic plots

# Evidence fusion + figures
cd ../Evidence_fusion_visual_dispalys
python member_e_feature_builder.py
```

Node B is the only stage that needs an external API key; every other stage runs
locally and is reproducible from the data in this repository.

---

## 8. Known limitations

These are stated deliberately — documenting the gaps is part of good curation.

- **Image-level vision labels are sparse** (3 of 946). Component fields rely on
  text heuristics or are left `unknown`; the website tags each record accordingly.
- **JD reviews could not be collected** (anti-scraping). The platform is kept in
  the schema with a value of 0 for transparency.
- **Platform volume is heavily skewed** toward Bilibili text; image signal is
  Xiaohongshu-only.
- **Visual-weight × pain-point** is an early-insight/demo chart because
  image-level visual-weight coverage is limited.

---

## 9. Further documentation

- [`docs/DATA_DICTIONARY_AND_VERSIONING.md`](docs/DATA_DICTIONARY_AND_VERSIONING.md)
  — dataset version scheme (v0→v4), version-control practices, and a full field
  dictionary for `feature_database.csv`.
- [`docs/ETHICS_AND_RISK.md`](docs/ETHICS_AND_RISK.md) — bias considerations,
  privacy limits, and responsible-practice notes (incl. a credentials-in-repo
  fix to action).

## 10. Course context

INFO 202 — *Data Curation*. Deliverables and the project plan live under
`zuoyeyaoqiu/` and `Project_Documents/`. Per the assignment, all delivered text
(this README, the report, and the website) is in **English**.
