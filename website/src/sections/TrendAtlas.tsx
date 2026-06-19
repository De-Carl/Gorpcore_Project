import { motion, useReducedMotion } from "framer-motion";
import TopoBackground from "../components/TopoBackground";
import SectionHeading from "../components/SectionHeading";
import { fadeRise, viewportOnce } from "../lib/motion";

/** Terms scale by curated weight (1–10). kind drives color. */
const terms: { word: string; weight: number; kind: "design" | "tone" }[] = [
  { word: "Utility", weight: 10, kind: "design" },
  { word: "Functional", weight: 9, kind: "design" },
  { word: "Earthy Tones", weight: 9, kind: "tone" },
  { word: "Layering", weight: 8, kind: "design" },
  { word: "Pocket", weight: 8, kind: "design" },
  { word: "Zipper", weight: 7, kind: "design" },
  { word: "Neutral Tones", weight: 7, kind: "tone" },
  { word: "Loose Fit", weight: 7, kind: "design" },
  { word: "Techwear", weight: 6, kind: "design" },
  { word: "Breathable", weight: 6, kind: "tone" },
  { word: "Reflective", weight: 5, kind: "design" },
  { word: "Muted", weight: 5, kind: "tone" },
  { word: "Durable", weight: 5, kind: "tone" },
  { word: "Modular", weight: 4, kind: "design" },
];

/** Map a 1–10 weight onto a font-size in rem. */
const sizeFor = (w: number) => 1 + (w / 10) * 3.2;

/** Pulsing map-marker beacon, pure decoration. */
function Beacon({
  className,
  delay = "0s",
}: {
  className: string;
  delay?: string;
}) {
  return (
    <span aria-hidden className={`absolute h-2 w-2 ${className}`}>
      <span
        className="ping-ring absolute -inset-1 rounded-full border border-hivis/70"
        style={{ animationDelay: delay }}
      />
      <span className="block h-2 w-2 rounded-full bg-hivis/80" />
    </span>
  );
}

export default function TrendAtlas() {
  const reduced = useReducedMotion();
  return (
    <section className="relative overflow-hidden bg-charcoal px-6 py-24 text-bone md:px-12 md:py-36">
      <TopoBackground stroke="rgba(124,139,107,0.16)" />
      {/* scattered survey beacons over the topo field */}
      <Beacon className="left-[12%] top-[22%] hidden md:block" />
      <Beacon className="right-[10%] top-[38%] hidden md:block" delay="1s" />
      <Beacon className="left-[22%] bottom-[14%] hidden md:block" delay="2s" />
      <div className="relative mx-auto max-w-6xl">
        <SectionHeading
          light
          index="03"
          kicker="Trend Atlas"
          title="The visual word cloud."
          intro="The data-driven mood board: every term below is weighted by how often it surfaces in curated consumer language. Design vocabulary in sage, tone vocabulary in sand — the season's voice, at a glance."
        />

        {/* Word cloud */}
        <div className="flex flex-wrap items-baseline justify-center gap-x-8 gap-y-4 py-8 text-center md:gap-x-12 md:py-12">
          {terms.map((t, i) => (
            <motion.span
              key={t.word}
              initial={{ opacity: 0, scale: 0.7, y: 18 }}
              whileInView={{ opacity: 1, scale: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{
                duration: 0.6,
                delay: 0.05 * i,
                ease: [0.22, 1, 0.36, 1],
              }}
              whileHover={{ scale: 1.06, color: "#E4571B" }}
              className={`cursor-default font-display font-600 leading-none tracking-tight ${
                t.kind === "design" ? "text-sage" : "text-sand"
              }`}
              style={{ fontSize: `clamp(1rem, ${sizeFor(t.weight)}vw + 0.6rem, ${sizeFor(t.weight)}rem)` }}
            >
              {/* inner span floats gently forever; outer span owns the entrance */}
              <motion.span
                className="inline-block"
                animate={reduced ? undefined : { y: [0, -5 - (i % 3) * 2, 0] }}
                transition={{
                  duration: 4 + (i % 4),
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: i * 0.3,
                }}
              >
                {t.word}
                <span className="ml-1 align-super font-mono text-[10px] text-bone/40">
                  {t.weight}
                </span>
              </motion.span>
            </motion.span>
          ))}
        </div>

        {/* Drop-in slot for the rendered atlas */}
        <motion.div
          variants={fadeRise}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mt-16"
        >
          <div className="spec-frame spec-frame--light overflow-hidden p-1">
            <img
              src="/charts/fig_visual_wordcloud.png"
              alt="Visual word cloud rendered from the curated multimodal corpus"
              loading="lazy"
              className="w-full bg-bone"
            />
          </div>
          <p className="spec-label mt-3 text-bone/50">
            Fig. 03 — Trend atlas, rendered from the curated multimodal corpus
            (word frequency × design-field weighting)
          </p>
        </motion.div>

        {/* Image word cloud — the corpus drawn with itself */}
        <motion.div
          variants={fadeRise}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mt-16"
        >
          <div className="spec-frame overflow-hidden p-1">
            <img
              src="/charts/fig_image_wordcloud.png"
              alt="Image word cloud: 604 curated Gorpcore outfit photos tiled into a mountain silhouette, ordered by colour family"
              loading="lazy"
              className="w-full bg-charcoal"
            />
          </div>
          <p className="spec-label mt-3 text-bone/50">
            Fig. 04 — Image word cloud: the curated outfit corpus tiled into a
            mountain silhouette, ordered by colour family (light at the peaks →
            earth tones at the base)
          </p>
        </motion.div>
      </div>
    </section>
  );
}
