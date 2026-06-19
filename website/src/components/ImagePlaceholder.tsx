/**
 * Clearly-labeled slot where a real photo / mood-board image will drop in.
 * Keeps the spec-sheet look: thin rule, corner ticks, mono label.
 */
export default function ImagePlaceholder({
  label,
  ratio = "aspect-[4/5]",
  className = "",
}: {
  label: string;
  ratio?: string;
  className?: string;
}) {
  return (
    <div
      className={`spec-frame relative flex ${ratio} w-full items-center justify-center overflow-hidden bg-sand/40 ${className}`}
    >
      {/* faint diagonal hatch to read as "empty slot" */}
      <div
        aria-hidden
        className="absolute inset-0 opacity-[0.18]"
        style={{
          backgroundImage:
            "repeating-linear-gradient(135deg, transparent 0 10px, #3F4A34 10px 11px)",
        }}
      />
      {/* hi-vis scan line sweeps through while the parent .group is hovered */}
      <div
        aria-hidden
        className="absolute inset-x-0 top-0 h-1/4 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
      >
        <div className="scan-sweep h-full w-full bg-gradient-to-b from-transparent via-hivis/25 to-transparent" />
      </div>
      <div className="relative px-4 text-center">
        <span className="spec-label block text-olive/80">[ image slot ]</span>
        <span className="mt-1 block font-mono text-[11px] text-charcoal/60">
          {label}
        </span>
      </div>
    </div>
  );
}
