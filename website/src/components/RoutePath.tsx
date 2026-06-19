/**
 * Decorative trail-map route: a marching dashed line from "MTN" to "CITY"
 * with pulsing waypoint beacons. Pure ornament — aria-hidden, sits behind
 * section content. All animation is CSS, gated by prefers-reduced-motion.
 */
const waypoints = [
  { x: 60, y: 96, label: "MTN" },
  { x: 470, y: 56, label: "PASS" },
  { x: 880, y: 88, label: "CITY" },
];

export default function RoutePath({ className = "" }: { className?: string }) {
  return (
    <div aria-hidden className={`pointer-events-none ${className}`}>
      <svg
        viewBox="0 0 940 140"
        className="h-auto w-full"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* the route itself */}
        <path
          className="route-march"
          d="M60,96 C180,30 300,110 470,56 C640,2 760,120 880,88"
          fill="none"
          stroke="#7C8B6B"
          strokeWidth="1.5"
        />
        {/* waypoint beacons */}
        {waypoints.map((w) => (
          <g key={w.label}>
            <circle className="ping-ring" cx={w.x} cy={w.y} r="10" fill="none" stroke="#E4571B" strokeWidth="1" />
            <circle cx={w.x} cy={w.y} r="3.5" fill="#E4571B" />
            <text
              x={w.x}
              y={w.y - 16}
              textAnchor="middle"
              fill="#1C1E1A"
              fillOpacity="0.45"
              style={{ font: "500 10px 'JetBrains Mono', monospace", letterSpacing: "0.18em" }}
            >
              {w.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
