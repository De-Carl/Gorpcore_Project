/**
 * Infinite spec-tape marquee band used as a section divider.
 * The track holds the item list twice so the -50% loop is seamless;
 * animation is disabled under prefers-reduced-motion via CSS.
 */
const items = [
  "Lightweight Gorpcore",
  "Engineered for the Commute",
  "Urban-Outdoor",
  "Image–Text Cross-Verified",
  "Earth Tones / Hi-Vis Accent",
  "SS Season Playbook",
];

export default function Marquee({ dark = false }: { dark?: boolean }) {
  const tape = [...items, ...items];
  return (
    <div
      aria-hidden
      className={`overflow-hidden border-y py-3 ${
        dark
          ? "border-bone/15 bg-charcoal text-bone/60"
          : "border-charcoal/15 bg-bone text-charcoal/60"
      }`}
    >
      <div className="marquee-track flex w-max items-center">
        {tape.map((item, i) => (
          <span
            key={i}
            className="flex items-center whitespace-nowrap font-mono text-[11px] uppercase tracking-widecaps"
          >
            <span className="px-6">{item}</span>
            <span className="text-hivis">◆</span>
          </span>
        ))}
      </div>
    </div>
  );
}
