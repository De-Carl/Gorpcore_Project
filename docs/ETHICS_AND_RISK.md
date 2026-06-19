# Ethics & Risk Statement

> Bias considerations, privacy limits, and responsible-practice notes for the
> Gorpcore Trend Intelligence data-curation project. Required by the course
> brief ("Ethics & Risk Statement: bias considerations, privacy limits, and
> responsible practice").

This project curates public consumer data from Chinese social and e-commerce
platforms. Because that data is scraped, multimodal, and used to make design
recommendations, it carries bias, privacy, and reliability risks. We document
them here rather than hide them — transparency about limitations is part of
trustworthy curation.

---

## 1. Bias considerations

### 1.1 Sampling / platform bias
- **Severe platform skew.** ~95.7% of text records come from Bilibili (danmaku +
  comments); Xiaohongshu provides ~3.1% but is the **only** image source; Taobao
  ~1.2%; JD 0%. Any "consumer voice" conclusion is therefore weighted heavily
  toward Bilibili's (younger, video-native) audience, and every visual finding is
  effectively a *Xiaohongshu* finding.
- **Keyword-driven selection bias.** Posts were collected via curated hashtags
  (`#机能风穿搭`, `#Gorpcore`). This pre-filters toward content already labelled as
  gorpcore by creators, missing adjacent or emerging styles that don't use the tag.
- **Region & language bias.** All data is Chinese-language and China-market. The
  resulting palette/material/silhouette recommendations should **not** be assumed
  to generalise to other markets.

### 1.2 Idealisation bias
- Social posts (especially Xiaohongshu) are **curated, idealised** self-presentation
  — flattering photos, sponsored looks, aspirational styling. This systematically
  over-represents what looks good on camera and under-represents everyday wear.
  The pipeline mitigates this by **cross-checking image labels against review text**
  (Node C) and weighting **negative review signal** (pain points) from e-commerce,
  but the bias is reduced, not removed.

### 1.3 Annotation / model bias
- **Sparse visual labels.** Only 3 of 946 images carry a vision-LLM (Qwen-VL-Max)
  label. The remaining component attributes come from **text heuristics** or are
  left **unknown**. We do **not** claim full image-level component detection;
  the website tags every record with its provenance (vision label / text heuristic
  / colour only) so no inferred field is mistaken for a measured one.
- **Model bias.** Both the vision model and the text heuristics inherit the biases
  of their training data and keyword lists (e.g. colour-name and material-term
  dictionaries). Colour extraction (K-Means) is lighting- and crop-sensitive.

### 1.4 Sample-size caveats
- Pain points are de-duplicated to **n = 120**. Counts like "zipper = 1" are too
  small to be statistically meaningful and are presented as directional signal,
  not proof.

---

## 2. Privacy limits

### 2.1 Nature of the data
- All collected content is **publicly posted** social/e-commerce material. We store
  post text, images, `note_id`, public URLs, and timestamps. We do **not**
  deliberately collect or publish real names, contact details, or other direct PII,
  and no user-identity profiling is performed.
- However, scraped social content **can still be re-identifying** (a `note_id` or
  image links back to a real creator's account). This dataset is intended for an
  **internal course/design context only** and should not be redistributed or used
  to target, contact, or profile individuals.

### 2.2 ⚠️ Action required — credentials committed to the repo
Two secrets were found committed to the repository:

1. **`Dataset/xhs/xiaohongshu_auth_state.json`** — a Xiaohongshu **login/cookie
   state file**. Anyone with repo access could reuse the session.
2. **`Gorpcore_Agent/preliminary/agent_core.py`** — a **hard-coded Aliyun
   DashScope API key** (`API_KEY = "sk-…"`). This can be abused to run up billing
   on the owner's account.

- **Recommended remediation:**
  1. Cookie: `git rm --cached Dataset/xhs/xiaohongshu_auth_state.json`, add it to
     `.gitignore`, and **log out / re-login** on Xiaohongshu to invalidate it.
     *(Done in this repo: untracked + gitignored; session invalidation is the
     owner's manual step.)*
  2. API key: **rotate/revoke the key in the Aliyun console immediately**, then
     load it from an environment variable instead of hard-coding
     (e.g. `os.environ["DASHSCOPE_API_KEY"]`).
  3. Both secrets may persist in **git history**. If the repo was ever pushed,
     scrub history (e.g. `git filter-repo`) in addition to rotating the secrets.

### 2.3 Storage & retention
- Raw images and text are kept locally under `Dataset/`. They should be deleted or
  access-restricted once the course deliverable is graded, and never published with
  the website build (the site ships only 9 hand-checked sample images + aggregate
  charts, not the full corpus).

---

## 3. Responsible-practice notes

- **Respect platform limits.** JD review collection was **blocked by anti-scraping
  measures and we did not attempt to circumvent it** — JD is recorded as 0 records
  rather than forced. Scrapers should run at modest rates and honour each site's
  Terms of Service and `robots` rules.
- **Human-in-the-loop.** The pipeline never auto-publishes machine judgments: Node D
  consolidates **auditable human review** (accept / revise / reject / pending), so a
  person owns the final curation decisions.
- **Auditability.** Every stage writes its own CSV + JSON log; every figure on the
  website traces back to a file in the repo. Numbers are reported as-measured, and
  known gaps (sparse labels, blocked JD, platform skew) are stated explicitly.
- **No overclaiming.** Recommendations are framed as *directional design signal*
  from a biased, China-market, gorpcore-tagged sample — not as market-wide truth.
- **Intended use.** Outputs support a design team's creative direction. They must
  **not** be used for individual targeting, surveillance, or any decision affecting
  the people whose posts were collected.

---

## 4. Residual risks (accepted, with mitigation)

| Risk | Severity | Mitigation in place |
| --- | --- | --- |
| Platform skew distorts "consumer voice" | High | Stated explicitly; image vs. text findings separated |
| Idealised social posts | Medium | Node C image↔text cross-check; e-commerce negatives weighted |
| Sparse / heuristic visual labels | Medium | Per-record provenance tags; no full-detection claim |
| Committed login cookie | High | Remediation steps in §2.2 (action required) |
| Re-identification of public posters | Medium | Internal use only; full corpus not published |
| Small pain-point counts | Low | Presented as directional, not statistical proof |
