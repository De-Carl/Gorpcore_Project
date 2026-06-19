import { motion, useReducedMotion } from "framer-motion";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { fadeRise, staggerParent, viewportOnce } from "../lib/motion";
import SectionHeading from "../components/SectionHeading";
import Counter from "../components/Counter";

/**
 * Demand signal → design move pairings. `value` is the real de-duplicated
 * mention count of each pain point in the curated review corpus (n = 120),
 * extracted in the evidence-fusion stage. Nothing here is normalised or
 * invented — these are the raw counts behind the design board.
 */
const signals = [
  { name: "Price sensitivity", value: 68, move: "Value engineering · tiered materials" },
  { name: "Breathability", value: 29, move: "Ventilation systems · breathable membranes" },
  { name: "Commute fit", value: 8, move: "Daily-wear silhouettes · stowable features" },
  { name: "Durability", value: 5, move: "Reinforced ripstop construction" },
  { name: "Weight", value: 5, move: "Reduced-weight fabrics · minimal hardware" },
  { name: "Silhouette", value: 4, move: "Refined urban cut" },
  { name: "Zipper reliability", value: 1, move: "Sealed, dependable zipper systems" },
];

/**
 * Platform mix by share of raw text records collected (~39.6K total).
 * Bilibili danmaku + comments dominate volume; JD was blocked during
 * collection and contributes no usable records.
 */
const platforms = [
  { name: "Bilibili", value: 95.7 },
  { name: "Xiaohongshu", value: 3.1 },
  { name: "Taobao", value: 1.2 },
  { name: "JD (blocked)", value: 0 },
];
const platformColors = ["#3F4A34", "#7C8B6B", "#C8BBA1", "#E4571B"];

const stats = [
  { value: 40, suffix: "K+", label: "Consumer signals curated" },
  { value: 946, suffix: "", label: "Curated outfit images" },
  { value: 4, suffix: "", label: "Platforms, cross-sourced" },
  { value: 497, suffix: "", label: "Image–text cross-linked" },
];

function SignalRow({ s, max }: { s: (typeof signals)[number]; max: number }) {
  const reduced = useReducedMotion();
  return (
    <motion.li
      variants={fadeRise}
      className="group grid items-center gap-x-6 gap-y-2 border-b border-charcoal/10 py-4 transition-colors duration-300 hover:bg-bone/70 md:grid-cols-12"
    >
      <span className="font-display text-base font-500 md:col-span-3">
        {s.name}
      </span>
      <div className="flex items-center gap-3 md:col-span-5">
        <div className="h-2 flex-1 overflow-hidden bg-charcoal/10">
          <motion.div
            className="h-full bg-olive transition-colors duration-300 group-hover:bg-hivis"
            initial={reduced ? { scaleX: 1 } : { scaleX: 0 }}
            whileInView={{ scaleX: s.value / max }}
            viewport={viewportOnce}
            transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
            style={{ originX: 0, width: "100%" }}
          />
        </div>
        <Counter
          to={s.value}
          suffix=""
          duration={1}
          className="spec-label w-10 text-right text-charcoal/60"
        />
      </div>
      <span className="flex items-center gap-2 text-sm text-charcoal/70 md:col-span-4">
        <motion.span
          aria-hidden
          className="text-hivis"
          initial={reduced ? false : { opacity: 0, x: -8 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={viewportOnce}
          transition={{ duration: 0.5, delay: 0.5 }}
        >
          →
        </motion.span>
        {s.move}
      </span>
    </motion.li>
  );
}

export default function TrendSignals() {
  const max = Math.max(...signals.map((s) => s.value));
  return (
    <section className="relative bg-sand/30 px-6 py-24 md:px-12 md:py-36">
      <div className="mx-auto max-w-6xl">
        <SectionHeading
          index="02"
          kicker="Trend Signals"
          title="What consumers reject — and what to design instead."
          intro="Every rejection signal in the corpus maps to a concrete design move. Read left to right: the complaint, its weight in the data, the answer on the board."
        />

        {/* A) Signal → design move bars */}
        <motion.ul
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="border-t border-charcoal/10"
        >
          {signals.map((s) => (
            <SignalRow key={s.name} s={s} max={max} />
          ))}
        </motion.ul>
        <p className="spec-label mt-4 text-charcoal/50">
          Curated, de-duplicated pain-point mentions (n = 120) · bar length
          relative to the top complaint
        </p>

        {/* B) Evidence at a glance */}
        <motion.div
          variants={staggerParent}
          initial="hidden"
          whileInView="visible"
          viewport={viewportOnce}
          className="mt-20 grid gap-10 md:grid-cols-12"
        >
          <motion.div variants={fadeRise} className="md:col-span-8">
            <h3 className="spec-label mb-8 text-charcoal/60">
              Evidence at a glance
            </h3>
            <div className="grid grid-cols-2 gap-px bg-charcoal/15 lg:grid-cols-4">
              {stats.map((stat) => (
                <div key={stat.label} className="bg-bone p-6">
                  <Counter
                    to={stat.value}
                    suffix={stat.suffix}
                    className="font-display text-4xl font-600 tracking-tight md:text-5xl"
                  />
                  <p className="mt-2 text-sm text-charcoal/65">{stat.label}</p>
                </div>
              ))}
            </div>
            <p className="mt-4 max-w-xl text-sm leading-relaxed text-charcoal/60">
              A large multimodal corpus of consumer signals, outfit images and
              competitor reviews — curated across four platforms and
              cross-verified between image and text to filter idealised social
              posts.
            </p>
          </motion.div>

          {/* Platform mix donut */}
          <motion.div variants={fadeRise} className="md:col-span-4">
            <h3 className="spec-label mb-8 text-charcoal/60">Platform mix</h3>
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={platforms}
                    dataKey="value"
                    nameKey="name"
                    innerRadius="62%"
                    outerRadius="95%"
                    paddingAngle={2}
                    stroke="none"
                    isAnimationActive
                  >
                    {platforms.map((p, i) => (
                      <Cell key={p.name} fill={platformColors[i]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: number, n: string) => [`${v}%`, n]}
                    contentStyle={{
                      background: "#1C1E1A",
                      border: "none",
                      color: "#F4F2EC",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12,
                    }}
                    itemStyle={{ color: "#F4F2EC" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="mt-4 space-y-1">
              {platforms.map((p, i) => (
                <li
                  key={p.name}
                  className="flex items-center gap-2 font-mono text-[11px] text-charcoal/65"
                >
                  <span
                    aria-hidden
                    className="h-2 w-2"
                    style={{ background: platformColors[i] }}
                  />
                  {p.name} · {p.value}%
                </li>
              ))}
            </ul>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
