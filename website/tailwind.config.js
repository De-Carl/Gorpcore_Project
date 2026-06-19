/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        olive: "#3F4A34",
        sage: "#7C8B6B",
        khaki: "#C8BBA1",
        sand: "#DDD3BE",
        charcoal: "#1C1E1A",
        bone: "#F4F2EC",
        hivis: "#E4571B",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "system-ui", "sans-serif"],
        body: ["'Inter'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        widecaps: "0.18em",
      },
    },
  },
  plugins: [],
};
