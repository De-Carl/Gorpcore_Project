import { useLayoutEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { fadeRise, staggerParent, viewportOnce } from "../lib/motion";
import SectionHeading from "../components/SectionHeading";

gsap.registerPlugin(ScrollTrigger);

/**
 * Curated outfit records backing the recommendations.
 *
 * These are real rows from the curated feature database
 * (Evidence_fusion_visual_dispalys/output/feature_database.csv): the image is
 * the post-quality-gate Xiaohongshu photo, the two swatches are the dominant
 * colours extracted by k-means, and `source` is the provenance of the
 * structured attributes (node_b vision label, text heuristic, or unknown).
 * Nothing here is mocked — empty fields are shown as "—" rather than invented.
 */
type Record = {
  file: string;
  id: string;
  primary: string;
  primaryHex: string;
  secondaryHex: string;
  scenario: string;
  sentiment: string;
  source: "node_b" | "text_heuristic" | "unknown";
};

const records: Record[] = [
  { file: "/evidence/outfit_01.webp", id: "GC-6A030F", primary: "olive green", primaryHex: "#747360", secondaryHex: "#505339", scenario: "—", sentiment: "neutral", source: "unknown" },
  { file: "/evidence/outfit_02.webp", id: "GC-69D104", primary: "khaki / beige", primaryHex: "#A3977B", secondaryHex: "#CDD0CC", scenario: "Outdoor", sentiment: "neutral", source: "text_heuristic" },
  { file: "/evidence/outfit_03.webp", id: "GC-698F2F", primary: "black", primaryHex: "#141813", secondaryHex: "#3D4028", scenario: "Outdoor", sentiment: "neutral", source: "text_heuristic" },
  { file: "/evidence/outfit_04.webp", id: "GC-68FB6C", primary: "blue", primaryHex: "#8D94A1", secondaryHex: "#ACAFBC", scenario: "—", sentiment: "neutral", source: "unknown" },
  { file: "/evidence/outfit_05.webp", id: "GC-6A0B15", primary: "brown", primaryHex: "#64543F", secondaryHex: "#9F7D55", scenario: "—", sentiment: "positive", source: "unknown" },
  { file: "/evidence/outfit_06.webp", id: "GC-683EC1", primary: "white", primaryHex: "#DCDDDC", secondaryHex: "#C9C9C8", scenario: "—", sentiment: "neutral", source: "unknown" },
  { file: "/evidence/outfit_07.webp", id: "GC-697B27", primary: "gray", primaryHex: "#A8AAAA", secondaryHex: "#898886", scenario: "Outdoor", sentiment: "neutral", source: "text_heuristic" },
  { file: "/evidence/outfit_08.webp", id: "GC-6964A7", primary: "charcoal", primaryHex: "#342E29", secondaryHex: "#151311", scenario: "Outdoor", sentiment: "neutral", source: "text_heuristic" },
  { file: "/evidence/outfit_09.webp", id: "GC-6863E5", primary: "olive green", primaryHex: "#668230", secondaryHex: "#C8D4E0", scenario: "Outdoor", sentiment: "neutral", source: "text_heuristic" },
];

function ProvenanceTag({ source }: { source: Record["source"] }) {
  const map = {
    node_b: { text: "vision label", cls: "text-hivis border-hivis/50" },
    text_heuristic: { text: "text heuristic", cls: "text-sage border-sage/50" },
    unknown: { text: "color only", cls: "text-charcoal/45 border-charcoal/20" },
  } as const;
  const m = map[source];
  return (
    <span className={`font-mono text-[9px] uppercase tracking-wide border px-1.5 py-0.5 ${m.cls}`}>
      {m.text}
    </span>
  );
}

function Swatch({ hex }: { hex: string }) {
  return (
    <span className="flex items-center gap-1">
      <span
        aria-hidden
        className="h-3 w-3 border border-charcoal/15"
        style={{ background: hex }}
      />
      <span className="font-mono text-[9px] uppercase text-charcoal/55">{hex}</span>
    </span>
  );
}

export default function EvidenceGallery() {
  const sectionRef = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  // Desktop: pin the section and scrub the card track horizontally —
  // the gallery reads as one long filmstrip of curated records.
  // Tablet/mobile and reduced-motion keep the normal vertical grid.
  useLayoutEffect(() => {
    if (reduced) return;
    const mm = gsap.matchMedia();
    mm.add("(min-width: 1024px)", () => {
      const track = trackRef.current!;
      const distance = () => track.scrollWidth - window.innerWidth + 96;
      gsap.to(track, {
        x: () => -distance(),
        ease: "none",
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: () => `+=${distance()}`,
          scrub: 0.6,
          pin: true,
          invalidateOnRefresh: true,
        },
      });
    });
    return () => mm.revert();
  }, [reduced]);

  return (
    <section
      ref={sectionRef}
      className="relative overflow-hidden bg-sand/30 py-24 md:py-36 lg:flex lg:h-screen lg:flex-col lg:justify-center lg:py-0"
    >
      <div className="mx-auto w-full max-w-6xl px-6 md:px-12 lg:mb-12">
        <SectionHeading
          index="05"
          kicker="Curated Evidence"
          title="Every call, grounded in a record."
          intro="A sample of the curated outfit corpus. Each look is a real Xiaohongshu image that cleared the quality gate; the swatches are its machine-extracted dominant colours, and the tag shows where each structured attribute came from — vision label, text heuristic, or colour extraction only."
        />
      </div>

      <motion.div
        ref={trackRef}
        variants={staggerParent}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        className="grid gap-6 px-6 sm:grid-cols-2 md:px-12 lg:flex lg:w-max lg:gap-8"
      >
        {records.map((r) => (
          <motion.figure
            key={r.id}
            variants={fadeRise}
            whileHover={{ y: -6 }}
            transition={{ duration: 0.3 }}
            className="group lg:w-[300px] lg:shrink-0"
          >
            <div className="spec-frame relative aspect-[4/5] w-full overflow-hidden bg-sand/40">
              <img
                src={r.file}
                alt={`Curated gorpcore outfit ${r.id}, primary colour ${r.primary}`}
                loading="lazy"
                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
              />
            </div>
            <figcaption className="mt-3 border-l-2 border-hivis/70 pl-3">
              <span className="spec-label flex items-center justify-between text-charcoal/50">
                {r.id}
                <ProvenanceTag source={r.source} />
              </span>
              <div className="mt-2 flex items-center gap-3">
                <Swatch hex={r.primaryHex} />
                <Swatch hex={r.secondaryHex} />
              </div>
              <p className="mt-2 font-mono text-[10px] leading-relaxed text-charcoal/70">
                Primary: {r.primary} · Scenario: {r.scenario} · Sentiment: {r.sentiment}
              </p>
            </figcaption>
          </motion.figure>
        ))}

        {/* End-cap so the strip closes on a statement, not a cut edge */}
        <div className="hidden lg:flex lg:w-[300px] lg:shrink-0 lg:flex-col lg:justify-center">
          <p className="font-display text-2xl font-600 leading-snug tracking-tight">
            One schema.
            <br />
            <span className="text-hivis">Every record.</span>
          </p>
          <p className="spec-label mt-4 text-charcoal/50">
            Corpus sample · 9 of 946 curated looks
          </p>
        </div>
      </motion.div>
    </section>
  );
}
