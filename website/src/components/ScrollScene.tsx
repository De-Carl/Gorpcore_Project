import { useRef, type ReactNode } from "react";
import {
  motion,
  useMotionTemplate,
  useReducedMotion,
  useScroll,
  useTransform,
} from "framer-motion";

/**
 * Scroll-linked section choreography (scrubbed, not one-shot):
 *
 *  - "card": deck-of-cards feel. Entering, the section is a rounded,
 *    inset card that rises and unclips to full bleed as it locks in.
 *    Leaving, it sinks back, shrinks and dims — receding under the
 *    section that follows.
 *  - "rise": gentler y + opacity ramp for sections that sit directly
 *    on the page background.
 */
export default function ScrollScene({
  children,
  variant = "rise",
}: {
  children: ReactNode;
  variant?: "card" | "rise";
}) {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  // Two scrub timelines on the same section: one for the way in,
  // one for the way out.
  const { scrollYProgress: enter } = useScroll({
    target: ref,
    offset: ["start 108%", "start 28%"],
  });
  const { scrollYProgress: exit } = useScroll({
    target: ref,
    offset: ["end 75%", "end 15%"],
  });

  const isCard = variant === "card";

  // Card: clip-path unfolds from an inset rounded frame to full bleed.
  const inset = useTransform(enter, [0, 1], [isCard ? 5 : 0, 0]);
  const radius = useTransform(enter, [0, 1], [isCard ? 56 : 0, 0]);
  const clipPath = useMotionTemplate`inset(0% ${inset}% 0% ${inset}% round ${radius}px)`;

  // Enter rises hard; exit sinks, shrinks and dims under the next card.
  const y = useTransform(
    [enter, exit],
    (v: number[]) => (isCard ? 110 : 64) * (1 - v[0]) + (isCard ? 36 : 0) * v[1]
  );
  const scale = useTransform(
    [enter, exit],
    (v: number[]) =>
      (isCard ? 0.96 + 0.04 * v[0] : 1) - (isCard ? 0.06 : 0) * v[1]
  );
  const opacity = useTransform(
    [enter, exit],
    (v: number[]) =>
      (isCard ? 1 : 0.3 + 0.7 * v[0]) - (isCard ? 0.5 : 0) * v[1]
  );

  if (reduced) return <div>{children}</div>;

  return (
    <motion.div
      ref={ref}
      style={{ y, scale, opacity, clipPath }}
      className="relative will-change-transform"
    >
      {children}
    </motion.div>
  );
}
