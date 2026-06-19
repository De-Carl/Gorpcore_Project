import { motion } from "framer-motion";
import { fadeRise, viewportOnce } from "../lib/motion";

const team = [
  "Zisheng Chen",
  "Shang Ma",
  "Linxiao Du",
  "Chenye Zheng",
  "Guanzheng Chen",
];

export default function Footer() {
  return (
    <footer className="relative bg-charcoal px-6 py-16 text-bone md:px-12">
      <motion.div
        variants={fadeRise}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOnce}
        className="mx-auto max-w-6xl"
      >
        <div className="hairline mb-10" />

        <div className="grid gap-10 md:grid-cols-3">
          <div>
            <p className="font-display text-lg font-600 tracking-tight">
              Gorpcore Trend Intelligence
            </p>
            <p className="mt-2 text-sm text-bone/60">
              Group 12 · INFO 202 Data Curation, Lanzhou University.
            </p>
          </div>

          <div>
            <p className="spec-label mb-3 text-bone/50">Team</p>
            <ul className="space-y-1 text-sm text-bone/75">
              {team.map((name) => (
                <li key={name}>{name}</li>
              ))}
            </ul>
          </div>

          <div>
            <p className="spec-label mb-3 text-bone/50">Repository</p>
            <a
              href="https://github.com/De-Carl/Gorpcore_Project"
              target="_blank"
              rel="noreferrer"
              className="font-mono text-xs text-sage underline-offset-4 hover:text-hivis hover:underline"
            >
              github.com/De-Carl/Gorpcore_Project
            </a>
            <p className="mt-4 text-xs text-bone/50">
              Built on an AI-assisted multimodal data-curation pipeline.
            </p>
          </div>
        </div>

        <div className="mt-12 border-t border-bone/15 pt-6">
          <p className="font-display text-sm italic text-bone/60">
            “Not what is popular — what is defensible.”
          </p>
        </div>
      </motion.div>
    </footer>
  );
}
