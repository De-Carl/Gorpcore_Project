/**
 * Subtle topographic contour-line background. Pure SVG, tiled and slowly
 * drifting (drift is disabled under prefers-reduced-motion via CSS).
 */
export default function TopoBackground({
  className = "",
  stroke = "rgba(124,139,107,0.28)",
}: {
  className?: string;
  stroke?: string;
}) {
  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
    >
      <svg
        className="topo-drift absolute -inset-[160px] h-[calc(100%+320px)] w-[calc(100%+320px)]"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMid slice"
        viewBox="0 0 900 600"
      >
        <g fill="none" stroke={stroke} strokeWidth="1">
          {/* Hand-tuned nested contour rings, like a trail-map detail */}
          <path d="M120,300 C120,180 260,110 420,130 C580,150 700,240 690,340 C680,440 540,520 380,500 C220,480 120,420 120,300 Z" />
          {/* dash-drift turns this ring into a slowly crawling trail line */}
          <path className="dash-drift" d="M170,300 C170,210 280,150 415,168 C550,186 645,255 637,335 C629,415 510,478 375,460 C240,442 170,390 170,300 Z" />
          <path d="M220,300 C220,238 305,190 410,205 C515,220 590,270 584,330 C578,392 480,438 372,422 C264,406 220,362 220,300 Z" />
          <path d="M270,300 C270,262 330,228 405,240 C480,252 535,288 530,328 C525,368 450,398 372,386 C294,374 270,338 270,300 Z" />
          <path d="M320,302 C320,282 355,262 400,270 C445,278 478,300 474,324 C470,348 425,362 378,354 C331,346 320,322 320,302 Z" />
          <path d="M-40,80 C80,20 260,-10 420,30 C580,70 720,40 900,90" />
          <path d="M-40,130 C100,75 270,45 425,80 C580,115 730,90 900,140" />
          <path d="M-40,540 C120,580 300,610 470,570 C640,530 760,560 900,520" />
          <path className="dash-drift" d="M-40,490 C130,525 305,555 468,520 C631,485 765,510 900,470" />
        </g>
      </svg>
    </div>
  );
}
