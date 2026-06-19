import { useLayoutEffect, useRef } from "react";
import { motion, useReducedMotion } from "framer-motion";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { fadeRise, staggerParent, viewportOnce } from "../lib/motion";
import SectionHeading from "../components/SectionHeading";
import RoutePath from "../components/RoutePath";

gsap.registerPlugin(ScrollTrigger);

/** Pull-quote split into word tokens so GSAP can light them up on scrub. */
const quote: { text: string; tone?: "sage" | "hivis" }[] = [
  { text: "The" }, { text: "market" }, { text: "has" }, { text: "moved" },
  { text: "from" },
  { text: "“engineered", tone: "sage" }, { text: "for", tone: "sage" },
  { text: "extremes”", tone: "sage" },
  { text: "to" },
  { text: "“engineered", tone: "hivis" }, { text: "for", tone: "hivis" },
  { text: "the", tone: "hivis" }, { text: "commute.”", tone: "hivis" },
];

export default function Direction() {
  const quoteRef = useRef<HTMLQuoteElement>(null);
  const reduced = useReducedMotion();

  // Scroll-scrubbed reveal: words fade from ghosted to full as the quote
  // passes through the viewport.
  useLayoutEffect(() => {
    if (reduced) return;
    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".quote-word",
        { opacity: 0.16, y: 8 },
        {
          opacity: 1,
          y: 0,
          stagger: 0.06,
          ease: "none",
          scrollTrigger: {
            trigger: quoteRef.current,
            start: "top 85%",
            end: "top 35%",
            scrub: 0.6,
          },
        }
      );
    }, quoteRef);
    return () => ctx.revert();
  }, [reduced]);

  return (
    <section className="relative px-6 py-24 md:px-12 md:py-36">
      <div className="mx-auto max-w-6xl">
        <SectionHeading index="01" kicker="The Direction" title="Engineered for the commute." />

        <div className="grid gap-12 md:grid-cols-12">
          {/* Pull-quote, word-by-word scrub reveal */}
          <blockquote ref={quoteRef} className="relative md:col-span-7">
            <span
              aria-hidden
              className="absolute -left-4 top-0 h-full w-1 bg-hivis md:-left-8"
            />
            <p className="font-display text-2xl font-500 leading-snug tracking-tight md:text-4xl">
              {quote.map((w, i) => (
                <span
                  key={i}
                  className={`quote-word inline-block ${
                    w.tone === "sage"
                      ? "text-sage"
                      : w.tone === "hivis"
                        ? "text-hivis"
                        : ""
                  }`}
                >
                  {w.text}
                  {i < quote.length - 1 && " "}
                </span>
              ))}
            </p>
          </blockquote>

          {/* Supporting statements */}
          <motion.div
            variants={staggerParent}
            initial="hidden"
            whileInView="visible"
            viewport={viewportOnce}
            className="space-y-6 text-base leading-relaxed text-charcoal/75 md:col-span-5 md:text-lg"
          >
            <motion.p variants={fadeRise}>
              Consumers want the look and the preparedness of gorpcore — without
              the heat, the weight, and the visual excess of expedition gear.
            </motion.p>
            <motion.p variants={fadeRise}>
              The answer is a lightweight, city-ready line: technical credibility
              kept, mountain overkill stripped away.
            </motion.p>
            <motion.div variants={fadeRise} className="hairline" />
            <motion.p variants={fadeRise} className="spec-label text-charcoal/50">
              Thesis · validated against consumer signal
            </motion.p>
          </motion.div>
        </div>

        {/* Decorative trail route: mountain → pass → city */}
        <RoutePath className="mt-20 opacity-80 md:mt-28" />
      </div>
    </section>
  );
}
