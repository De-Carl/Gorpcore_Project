# import matplotlib

# matplotlib.use("Agg")
# import matplotlib.pyplot as plt
# import matplotlib.patches as mpatches
# import matplotlib.ticker as mticker
# import seaborn as sns
# import numpy as np

# labels = [
#     "Bilibili\n(danmaku)",
#     "Bilibili\n(comments)",
#     "Taobao\n(reviews)",
#     "Xiaohongshu\n(notes)",
#     "Xiaohongshu\n(images)",
#     "JD\n(reviews)",
# ]
# values = [33886, 5044, 481, 200, 1077, 0]

# COLORS = {
#     "bilibili": "#2E5E8C",
#     "bilibili2": "#5A87B0",
#     "taobao": "#2F8F83",
#     "xhs_notes": "#C8772E",
#     "xhs_images": "#E0A05A",
#     "jd": "#CBD2D9",
# }
# bar_colors = [
#     COLORS["bilibili"],
#     COLORS["bilibili2"],
#     COLORS["taobao"],
#     COLORS["xhs_notes"],
#     COLORS["xhs_images"],
#     COLORS["jd"],
# ]

# sns.set_theme(style="whitegrid", font="DejaVu Sans")
# fig, ax = plt.subplots(figsize=(10, 5.5), dpi=200)
# fig.patch.set_facecolor("white")
# ax.set_facecolor("white")

# x = np.arange(len(labels))
# bars = ax.bar(x, values, width=0.58, color=bar_colors, zorder=3, linewidth=0)

# for bar, val in zip(bars, values):
#     label = f"{val:,}" if val > 0 else "0\n(blocked)"
#     offset = max(values) * 0.012 if val > 0 else max(values) * 0.018
#     ax.text(
#         bar.get_x() + bar.get_width() / 2,
#         val + offset,
#         label,
#         ha="center",
#         va="bottom",
#         fontsize=9.5,
#         fontweight="bold",
#         color="#1F2A37",
#     )

# ax.set_xticks(x)
# ax.set_xticklabels(labels, fontsize=10, color="#1F2A37", linespacing=1.4)
# ax.set_ylabel("Records collected", fontsize=11, color="#44515F", labelpad=10)
# ax.set_ylim(0, max(values) * 1.22)
# ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
# ax.tick_params(axis="y", labelsize=9, colors="#7A8899")
# ax.tick_params(axis="x", length=0)

# ax.yaxis.grid(True, color="#E4E9EE", linewidth=0.8, zorder=0)
# ax.set_axisbelow(True)
# ax.spines[["top", "right", "left", "bottom"]].set_visible(False)

# ax.set_title(
#     "Raw Multimodal Corpus by Source  (Dataset v0)",
#     fontsize=13,
#     fontweight="bold",
#     color="#1F3A5F",
#     pad=16,
#     loc="left",
# )

# legend_patches = [
#     mpatches.Patch(color=COLORS["bilibili"], label="Bilibili"),
#     mpatches.Patch(color=COLORS["taobao"], label="Taobao"),
#     mpatches.Patch(color=COLORS["xhs_notes"], label="Xiaohongshu"),
#     mpatches.Patch(color=COLORS["jd"], label="JD"),
# ]
# ax.legend(
#     handles=legend_patches,
#     loc="upper right",
#     frameon=False,
#     fontsize=9.5,
#     labelcolor="#44515F",
#     handlelength=1.2,
#     handleheight=1.0,
# )

# plt.tight_layout()
# plt.savefig("./fig_volume_v2.png", bbox_inches="tight", facecolor="white", dpi=200)
# plt.close()
# print("saved → ./fig_volume_v2.png")

# import matplotlib

# matplotlib.use("Agg")
# import matplotlib.pyplot as plt
# import matplotlib.patches as mpatches
# import numpy as np

# sizes = [6.8, 92.3, 0.9]
# labels = ["Positive", "Neutral", "Negative"]
# pcts = ["6.8%", "92.3%", "0.9%"]
# colors = ["#2F8F83", "#CBD2D9", "#C8772E"]
# explode = [0.03, 0.01, 0.06]

# fig, ax = plt.subplots(figsize=(6, 5.6), dpi=200)
# fig.patch.set_facecolor("white")
# ax.set_facecolor("white")

# wedges, _ = ax.pie(
#     sizes,
#     colors=colors,
#     explode=explode,
#     startangle=90,
#     counterclock=False,
#     wedgeprops=dict(width=0.46, edgecolor="white", linewidth=2.5),
#     shadow=False,
# )

# # centre text
# ax.text(
#     0,
#     0.08,
#     "39,602",
#     ha="center",
#     va="center",
#     fontsize=16,
#     fontweight="bold",
#     color="#1F2A37",
# )
# ax.text(
#     0, -0.18, "curated records", ha="center", va="center", fontsize=8.5, color="#7A8899"
# )

# # callout labels with leader lines
# callouts = [
#     # (wedge_index, angle_deg, label, pct, text_xy, line_end_r)
#     (0, 45, "Positive", "6.8%", (0.78, 0.72), 0.62),
#     (1, 224, "Neutral", "92.3%", (-0.95, -0.30), 0.62),
#     (2, 82, "Negative", "0.9%", (0.90, -0.62), 0.62),
# ]
# for idx, angle, lbl, pct, txy, r in callouts:
#     rad = np.deg2rad(90 - angle)
#     lx, ly = r * np.cos(rad), r * np.sin(rad)
#     tx, ty = txy
#     ax.annotate(
#         f"{lbl}\n{pct}",
#         xy=(lx, ly),
#         xytext=(tx, ty),
#         fontsize=9,
#         fontweight="bold",
#         color="#1F2A37",
#         ha="center",
#         va="center",
#         arrowprops=dict(
#             arrowstyle="-",
#             color=colors[idx],
#             lw=1.4,
#             connectionstyle="arc3,rad=0.0",
#         ),
#     )

# ax.set_title(
#     "Sentiment of 39,602 Curated Text Records",
#     fontsize=12,
#     fontweight="bold",
#     color="#1F3A5F",
#     pad=14,
#     loc="left",
#     x=0.02,
# )

# plt.tight_layout()
# plt.savefig("./fig_sentiment_v2.png", bbox_inches="tight", facecolor="white", dpi=200)
# plt.close()
# print("saved → ./fig_sentiment_v2.png")

# import matplotlib

# matplotlib.use("Agg")
# import matplotlib.pyplot as plt
# import matplotlib.ticker as mticker
# import seaborn as sns
# import numpy as np

# labels = [
#     "Zipper issues",
#     "Poor fit / silhouette",
#     "Too heavy",
#     "Not durable",
#     "Not commute-friendly",
#     "Not breathable",
#     "High price",
# ]
# values = [1, 4, 5, 5, 8, 29, 68]

# # gradient: low → muted amber, high → deep amber
# base = np.array([200, 119, 46]) / 255
# light = np.array([237, 195, 140]) / 255
# norm = np.array(values) / max(values)
# colors = [tuple(light + (base - light) * n) for n in norm]

# sns.set_theme(style="whitegrid", font="DejaVu Sans")
# fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
# fig.patch.set_facecolor("white")
# ax.set_facecolor("white")

# y = np.arange(len(labels))
# bars = ax.barh(y, values, height=0.58, color=colors, zorder=3, linewidth=0)

# # value labels — inside bar if wide enough, else outside
# for bar, val in zip(bars, values):
#     bw = bar.get_width()
#     if bw >= 10:
#         ax.text(
#             bw - 1.2,
#             bar.get_y() + bar.get_height() / 2,
#             str(val),
#             ha="right",
#             va="center",
#             fontsize=9.5,
#             fontweight="bold",
#             color="white",
#         )
#     else:
#         ax.text(
#             bw + 0.8,
#             bar.get_y() + bar.get_height() / 2,
#             str(val),
#             ha="left",
#             va="center",
#             fontsize=9.5,
#             fontweight="bold",
#             color="#1F2A37",
#         )

# ax.set_yticks(y)
# ax.set_yticklabels(labels, fontsize=10.5, color="#1F2A37")
# ax.set_xlabel(
#     "Curated mentions (de-duplicated)", fontsize=10, color="#44515F", labelpad=8
# )
# ax.set_xlim(0, max(values) * 1.18)
# ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: str(int(v))))
# ax.tick_params(axis="x", labelsize=9, colors="#7A8899")
# ax.tick_params(axis="y", length=0)

# ax.xaxis.grid(True, color="#E4E9EE", linewidth=0.8, zorder=0)
# ax.set_axisbelow(True)
# ax.spines[["top", "right", "left", "bottom"]].set_visible(False)

# ax.set_title(
#     "Top Consumer Pain-Point Signals for Gorpcore  (Node D)",
#     fontsize=12,
#     fontweight="bold",
#     color="#1F3A5F",
#     pad=14,
#     loc="left",
# )

# plt.tight_layout()
# plt.savefig("./fig_painpoints_v2.png", bbox_inches="tight", facecolor="white", dpi=200)
# plt.close()
# print("saved → ./fig_painpoints_v2.png")


import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import argparse
import numpy as np
import os
import json

plt.rcParams["axes.unicode_minus"] = False

# ── load data ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Render review bias figure")
parser.add_argument("--input", "-i", help="Path to taobao_reviews.json", default=None)
parser.add_argument(
    "--output", "-o", help="Path to output image file (png)", default=None
)
args = parser.parse_args()

base_dir = os.path.dirname(__file__)
taobao_path = None
if args.input:
    taobao_path = args.input
else:
    candidates = [
        os.path.join(base_dir, "taobao", "taobao_reviews.json"),
        os.path.join(base_dir, "taobao_reviews.json"),
        os.path.join(base_dir, "..", "taobao", "taobao_reviews.json"),
        os.path.join(base_dir, "..", "Dataset", "taobao", "taobao_reviews.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            taobao_path = p
            break
if taobao_path is None or not os.path.exists(taobao_path):
    tried = (args.input or "(no input provided)") + "\n" + "\n".join(candidates)
    raise FileNotFoundError("taobao_reviews.json not found. Tried: \n" + tried)

with open(taobao_path, encoding="utf-8") as f:
    reviews = json.load(f)["reviews"]

# determine output path
output_path = (
    args.output if args.output else os.path.join(base_dir, "fig_review_bias.png")
)

DEFAULT_PHRASES = [
    "系统默认好评",
    "默认好评",
    "此用户没有填写评价",
    "用户未及时做出评价",
    "评价方未及时",
]


def is_default(r):
    return any(p in r["content"] for p in DEFAULT_PHRASES)


defaults = [r for r in reviews if is_default(r)]
genuine = [r for r in reviews if not is_default(r) and len(r["content"].strip()) >= 10]
noise = [r for r in reviews if not is_default(r) and len(r["content"].strip()) < 10]

n_total, n_default, n_noise, n_genuine = (
    len(reviews),
    len(defaults),
    len(noise),
    len(genuine),
)

C_DEFAULT, C_NOISE, C_GENUINE = "#CBD2D9", "#E0A05A", "#2F8F83"
C_INK, C_NAVY, C_SUB = "#1F2A37", "#1F3A5F", "#7A8899"

fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(12, 5.4), dpi=200, gridspec_kw={"width_ratios": [1, 1.2]}
)
fig.patch.set_facecolor("white")
for ax in (ax1, ax2):
    ax.set_facecolor("white")

# ════════════════════════════════════════════════════════════════════════
# PANEL A — donut
# ════════════════════════════════════════════════════════════════════════
sizes = [n_default, n_noise, n_genuine]
colors = [C_DEFAULT, C_NOISE, C_GENUINE]
explode = [0.02, 0.06, 0.06]

ax1.pie(
    sizes,
    colors=colors,
    explode=explode,
    startangle=90,
    counterclock=False,
    wedgeprops=dict(width=0.46, edgecolor="white", linewidth=2.5),
)

ax1.text(
    0,
    0.10,
    "481",
    ha="center",
    va="center",
    fontsize=17,
    fontweight="bold",
    color=C_INK,
)
ax1.text(
    0, -0.12, "low-star reviews", ha="center", va="center", fontsize=8, color=C_SUB
)

# legend ordered to match the donut visually (largest first)
legend_items = [
    (
        C_DEFAULT,
        "System default (no content)",
        f"{n_default} — {n_default/n_total*100:.0f}%",
        False,
    ),
    (
        C_NOISE,
        "Too short (<10 chars)",
        f"{n_noise} — {n_noise/n_total*100:.0f}%",
        False,
    ),
    (
        C_GENUINE,
        "Genuine user review",
        f"{n_genuine} — {n_genuine/n_total*100:.0f}%",
        True,
    ),
]
for k, (color, text, val, bold) in enumerate(legend_items):
    y = -0.66 - k * 0.20
    ax1.add_patch(
        plt.Rectangle(
            (-0.98, y - 0.06), 0.11, 0.12, color=color, transform=ax1.transData
        )
    )
    ax1.text(
        -0.81,
        y,
        text,
        va="center",
        fontsize=8.5,
        color=C_INK,
        fontweight="bold" if bold else "normal",
    )
    ax1.text(
        1.15,
        y,
        val,
        va="center",
        ha="right",
        fontsize=8.5,
        color=color,
        fontweight="bold",
    )

ax1.set_xlim(-1.3, 1.3)
ax1.set_ylim(-1.35, 1.2)
ax1.set_title(
    "A.  Composition of 481 retrieved reviews",
    fontsize=10.5,
    fontweight="bold",
    color=C_NAVY,
    pad=10,
    loc="left",
    x=-0.12,
)

# ════════════════════════════════════════════════════════════════════════
# PANEL B — jitter strip (labels parked on the right of each group)
# ════════════════════════════════════════════════════════════════════════
rng = np.random.default_rng(42)
groups = [
    ("System\ndefault", [len(r["content"].strip()) for r in defaults], C_DEFAULT),
    ("Too\nshort", [len(r["content"].strip()) for r in noise], C_NOISE),
    ("Genuine\nreview", [len(r["content"].strip()) for r in genuine], C_GENUINE),
]
max_len = max(len(r["content"].strip()) for r in genuine)

for i, (lbl, lengths, color) in enumerate(groups):
    jitter = rng.uniform(-0.16, 0.16, size=len(lengths))
    ax2.scatter(
        np.full(len(lengths), i) + jitter,
        lengths,
        color=color,
        alpha=0.6,
        s=30,
        zorder=3,
        linewidth=0,
    )
    mean_val = np.mean(lengths)
    ax2.hlines(mean_val, i - 0.28, i + 0.28, colors=color, linewidth=2.8, zorder=4)
    # label parked to the RIGHT of each group, vertically at the mean
    ax2.annotate(
        f"avg {mean_val:.0f}",
        xy=(i + 0.28, mean_val),
        xytext=(i + 0.40, mean_val),
        va="center",
        ha="left",
        fontsize=8.5,
        color=color,
        fontweight="bold",
    )

# threshold line + label parked top-left (clear of all points)
ax2.axhline(10, color="#E05252", linewidth=1.3, linestyle="--", zorder=2)
ax2.text(
    2.62,
    max_len * 1.22,
    "—— Node D filter threshold (10 chars)",
    fontsize=8,
    color="#E05252",
    va="center",
    ha="right",
)

ax2.set_xticks([0, 1, 2])
ax2.set_xticklabels([g[0] for g in groups], fontsize=10.5, color=C_INK)
ax2.set_ylabel(
    "Review content length (characters)", fontsize=10, color="#44515F", labelpad=8
)
ax2.set_xlim(-0.55, 2.85)
ax2.set_ylim(-8, max_len * 1.32)
ax2.yaxis.grid(True, color="#E4E9EE", linewidth=0.8, zorder=0)
ax2.spines[["top", "right", "left", "bottom"]].set_visible(False)
ax2.tick_params(axis="x", length=0)
ax2.tick_params(axis="y", labelsize=9, colors=C_SUB)
ax2.set_title(
    "B.  Content length by review type",
    fontsize=10.5,
    fontweight="bold",
    color=C_NAVY,
    pad=10,
    loc="left",
)

fig.suptitle(
    "Challenge 2: E-Commerce Review Bias  —  "
    "91.9% of retrieved records carry no design signal",
    fontsize=11.5,
    fontweight="bold",
    color=C_NAVY,
    y=1.02,
)

plt.tight_layout()
plt.savefig(output_path, bbox_inches="tight", facecolor="white", dpi=200)
plt.close()
print(f"saved → {output_path}")
