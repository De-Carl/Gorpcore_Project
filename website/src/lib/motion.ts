import type { Variants } from "framer-motion";

/** Shared scroll-reveal variants: fade + rise. */
export const fadeRise: Variants = {
  hidden: { opacity: 0, y: 28 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] },
  },
};

/** Container that staggers its children in. */
export const staggerParent: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};

/** Standard viewport config: trigger once, slightly before fully on screen. */
export const viewportOnce = { once: true, margin: "-80px" } as const;
