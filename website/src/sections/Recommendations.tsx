import { motion } from "framer-motion";
import { fadeRise, staggerParent, viewportOnce } from "../lib/motion";
import SectionHeading from "../components/SectionHeading";

/* ---------- Colour panel ---------- */

const palette = [
  { name: "Olive / Army Green", hex: "#3F4A34", text: "#F4F2EC" },
  { name: "Khaki", hex: "#C8BBA1", text: "#1C1E1A" },
  { name: "Charcoal", hex: "#1C1E1A", text: "#F4F2EC" },
  { name: "Off-White", hex: "#F4F2EC", text: "#1C1E1A" },
  { name: "Navy", hex: "#232B3A", text: "#F4F2EC" },
  { name: "Reflective Accent", hex: "#E4571B", text: "#F4F2EC", accent: true },
];

function ColourPanel() {
  return (
    <div className="flex h-full flex-col">
      <ul className="grid flex-1 grid-cols-2 gap-2 sm:grid-cols-3">
        {palette.map((c, i) => (
          <motion.li
            key={c.hex}
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            whileHover={{ scale: 1.05, zIndex: 1 }}
            transition={{ duration: 0.45, delay: i * 0.06 }}
            className={`flex aspect-square flex-col justify-end p-3 ${
              c.accent ? "ring-1 ring-hivis ring-offset-2 ring-offset-bone" : ""
            }`}
            style={{ backgroundColor: c.hex, color: c.text }}
          >
            <span className="text-[11px] font-500 leading-tight opacity-90">
              {c.name}
            </span>
            <span className="font-mono text-[10px] uppercase opacity-70">
              {c.hex}
            </span>
          </motion.li>
        ))}
      </ul>
      <p className="spec-label mt-4 text-charcoal/50">
        Earth core · one high-vis accent, used sparingly
      </p>
    </div>
  );
}

/* ---------- Material panel ---------- */

const materials = [
  { name: "Matte nylon", weight: "core", note: "lightweight · low sheen" },
  { name: "Ripstop", weight: "core", note: "durable · reinforced grid" },
  { name: "Soft-shell", weight: "core", note: "breathable · city layers" },
  { name: "Heavy fleece", weight: "min", note: "minimised for city line" },
  { name: "Hard-shell", weight: "min", note: "minimised for city line" },
];

function MaterialPanel() {
  return (
    <div className="flex h-full flex-col">
      <ul className="flex flex-1 flex-col gap-3">
        {materials.map((m, i) => (
          <motion.li
            key={m.name}
            initial={{ opacity: 0, x: -16 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
            className={`flex items-center justify-between gap-3 border px-4 py-3 ${
              m.weight === "core"
                ? "border-olive/40 bg-sage/15"
                : "border-charcoal/15 bg-transparent opacity-60"
            }`}
          >
            <span className="font-display text-sm font-500">{m.name}</span>
            <span className="font-mono text-[10px] uppercase tracking-widecaps text-charcoal/60">
              {m.weight === "core" ? "● core" : "○ minimised"} · {m.note}
            </span>
          </motion.li>
        ))}
      </ul>
      <p className="spec-label mt-4 text-charcoal/50">
        Lightweight, breathable core · mountain weight stripped
      </p>
    </div>
  );
}

/* ---------- Silhouette panel ---------- */

const silhouettes = [
  { name: "Loose but refined", spec: "ease through body · clean line" },
  { name: "Oversize with structure", spec: "volume held by seams, not bulk" },
  { name: "Cropped + longline pairing", spec: "layer-ready proportions" },
  { name: "Commute-ready fit", spec: "moves on a bike, reads in an office" },
];

function SilhouettePanel() {
  return (
    <div className="flex h-full flex-col">
      <ul className="flex flex-1 flex-col divide-y divide-charcoal/10">
        {silhouettes.map((s, i) => (
          <li key={s.name} className="flex items-baseline gap-4 py-4">
            <span className="spec-label text-hivis">S{i + 1}</span>
            <div>
              <p className="font-display text-base font-500">{s.name}</p>
              <p className="font-mono text-[11px] text-charcoal/55">{s.spec}</p>
            </div>
          </li>
        ))}
      </ul>
      <p className="spec-label mt-4 text-charcoal/50">
        Volume without excess · cut for the street grid
      </p>
    </div>
  );
}

/* ---------- Functional details panel ---------- */

const details = [
  "Sealed / reflective zippers",
  "Stealth multi-pocket layouts",
  "Taped seams",
  "Detachable / quick-dry elements",
  "Underarm ventilation",
];

function DetailsPanel() {
  return (
    <div className="flex h-full flex-col">
      <ul className="flex flex-1 flex-wrap content-start gap-2">
        {details.map((d, i) => (
          <motion.li
            key={d}
            initial={{ opacity: 0, scale: 0.85 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: "-40px" }}
            transition={{ duration: 0.4, delay: i * 0.07 }}
            whileHover={{
              scale: 1.05,
              borderColor: "#E4571B",
              color: "#E4571B",
            }}
            className="cursor-default border border-charcoal/20 bg-bone px-4 py-2 font-mono text-[11px] uppercase tracking-wide text-charcoal/80"
          >
            {d}
          </motion.li>
        ))}
      </ul>
      <p className="spec-label mt-4 text-charcoal/50">
        Gorpcore signatures kept in the lightweight edit
      </p>
    </div>
  );
}

/* ---------- Section ---------- */

const panels = [
  { tag: "REC / 01", title: "Colour", body: <ColourPanel /> },
  { tag: "REC / 02", title: "Material", body: <MaterialPanel /> },
  { tag: "REC / 03", title: "Silhouette", body: <SilhouettePanel /> },
  { tag: "REC / 04", title: "Functional Details", body: <DetailsPanel /> },
];

export default function Recommendations() {
  return (
    <section className="relative px-6 py-24 md:px-12 md:py-36">
      <div className="mx-auto max-w-6xl">
        <SectionHeading
          index="04"
          kicker="Design Recommendations"
          title="The season design board."
          intro="Four spec cards a designer can act on next season — colour, material, silhouette and the functional details that keep the line credibly gorpcore."
        />

        <motion.div
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="grid gap-6 md:grid-cols-2"
        >
          {panels.map((p) => (
            <motion.article
              key={p.tag}
              variants={fadeRise}
              whileHover={{ y: -5 }}
              transition={{ duration: 0.3 }}
              className="spec-frame flex flex-col bg-bone p-6 transition-shadow duration-300 hover:shadow-[0_12px_40px_-16px_rgba(28,30,26,0.35)] md:p-8"
            >
              <header className="mb-6 flex items-baseline justify-between border-b border-charcoal/10 pb-4">
                <h3 className="font-display text-xl font-600 tracking-tight md:text-2xl">
                  {p.title}
                </h3>
                <span className="spec-label text-charcoal/50">{p.tag}</span>
              </header>
              {p.body}
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
