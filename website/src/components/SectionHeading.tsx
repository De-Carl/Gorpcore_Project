import { motion } from "framer-motion";
import { fadeRise, viewportOnce } from "../lib/motion";

/** Numbered, spec-sheet style section header. */
export default function SectionHeading({
  index,
  kicker,
  title,
  intro,
  light = false,
}: {
  index: string;
  kicker: string;
  title: string;
  intro?: string;
  light?: boolean;
}) {
  const rule = light ? "border-bone/25" : "border-charcoal/20";
  const sub = light ? "text-bone/60" : "text-charcoal/60";
  return (
    <motion.header
      variants={fadeRise}
      initial="hidden"
      whileInView="visible"
      viewport={viewportOnce}
      className="mb-12 md:mb-16"
    >
      <div className={`flex items-baseline gap-4 border-t ${rule} pt-4`}>
        <span className={`spec-label ${sub}`}>{index}</span>
        <span className={`spec-label ${sub}`}>{kicker}</span>
      </div>
      <h2 className="mt-4 font-display text-3xl font-600 leading-tight tracking-tight md:text-5xl">
        {title}
      </h2>
      {intro && (
        <p className={`mt-4 max-w-2xl text-base leading-relaxed md:text-lg ${sub}`}>
          {intro}
        </p>
      )}
    </motion.header>
  );
}
