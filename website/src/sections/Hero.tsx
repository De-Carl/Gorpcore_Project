import { useLayoutEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import TopoBackground from "../components/TopoBackground";

gsap.registerPlugin(ScrollTrigger);

const headlineWords = ["Lightweight", "Gorpcore"];

export default function Hero() {
  const sectionRef = useRef<HTMLElement>(null);
  const bgRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  // GSAP scrub choreography on the way out: the topo layer scrolls slower
  // than the page, while the headline block sinks, shrinks and dims —
  // the hero recedes into the distance as the brief takes over.
  useLayoutEffect(() => {
    if (reduced) return;
    const ctx = gsap.context(() => {
      gsap.to(bgRef.current, {
        yPercent: 24,
        ease: "none",
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });
      gsap.to(contentRef.current, {
        yPercent: 14,
        scale: 0.94,
        opacity: 0.15,
        ease: "none",
        scrollTrigger: {
          trigger: sectionRef.current,
          start: "top top",
          end: "bottom 25%",
          scrub: true,
        },
      });
    }, sectionRef);
    return () => ctx.revert();
  }, [reduced]);

  return (
    <section
      ref={sectionRef}
      className="relative flex min-h-[100svh] flex-col justify-between overflow-hidden bg-charcoal text-bone"
    >
      <div ref={bgRef} className="absolute inset-0">
        <TopoBackground stroke="rgba(124,139,107,0.30)" />
      </div>

      {/* Decorative slow-spinning reticle, map-instrument style */}
      <div
        aria-hidden
        className="absolute right-[8%] top-[18%] hidden h-44 w-44 md:block lg:h-56 lg:w-56"
      >
        <svg viewBox="0 0 100 100" className="spin-slow h-full w-full">
          <circle cx="50" cy="50" r="48" fill="none" stroke="rgba(244,242,236,0.18)" strokeWidth="0.6" strokeDasharray="3 4" />
          <circle cx="50" cy="50" r="34" fill="none" stroke="rgba(124,139,107,0.35)" strokeWidth="0.6" />
          <line x1="50" y1="0" x2="50" y2="12" stroke="#E4571B" strokeWidth="0.8" />
          <line x1="50" y1="88" x2="50" y2="100" stroke="rgba(244,242,236,0.3)" strokeWidth="0.6" />
          <line x1="0" y1="50" x2="12" y2="50" stroke="rgba(244,242,236,0.3)" strokeWidth="0.6" />
          <line x1="88" y1="50" x2="100" y2="50" stroke="rgba(244,242,236,0.3)" strokeWidth="0.6" />
        </svg>
        <span className="spec-label absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-bone/40">
          N 36°
        </span>
      </div>

      {/* Top spec bar */}
      <div className="relative z-10 flex items-center justify-between px-6 pt-6 md:px-12">
        <span className="spec-label text-bone/70">Trend Intelligence · SS Season</span>
        <span className="spec-label hidden text-bone/70 sm:block">
          Design Direction / Urban-Outdoor
        </span>
        <span className="spec-label text-hivis">REF 01</span>
      </div>

      {/* Headline block */}
      <div ref={contentRef} className="relative z-10 px-6 md:px-12">
        <motion.p
          initial={reduced ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="spec-label mb-6 text-sage"
        >
          A data-driven design direction for the urban-outdoor season
        </motion.p>

        <h1 className="font-display font-700 leading-[0.95] tracking-tight">
          {headlineWords.map((word, i) => (
            <span key={word} className="block overflow-hidden">
              <motion.span
                className="sheen-text block text-[15vw] md:text-[10rem]"
                initial={reduced ? false : { y: "110%" }}
                animate={{ y: 0 }}
                transition={{
                  duration: 0.9,
                  delay: 0.35 + i * 0.12,
                  ease: [0.22, 1, 0.36, 1],
                }}
              >
                {word}
                {i === 1 && <span className="text-hivis">.</span>}
              </motion.span>
            </span>
          ))}
        </h1>

        <motion.p
          initial={reduced ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.8 }}
          className="mt-8 max-w-xl text-base leading-relaxed text-bone/75 md:text-lg"
        >
          From hardcore mountain gear to a lighter, city-ready style — distilled
          from real consumer signal into a concrete design playbook.
        </motion.p>
      </div>

      {/* Bottom spec bar */}
      <motion.div
        initial={reduced ? false : { opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.1 }}
        className="relative z-10 px-6 pb-8 md:px-12"
      >
        <div className="hairline mb-4" />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="spec-label text-bone/60">
            Prepared for Anta / Li-Ning design teams
          </span>
          <span className="spec-label flex items-center gap-2 text-bone/60">
            Scroll
            <motion.span
              aria-hidden
              animate={reduced ? undefined : { y: [0, 5, 0] }}
              transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
            >
              ↓
            </motion.span>
          </span>
        </div>
      </motion.div>
    </section>
  );
}
