import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#06141b",
          panel: "#0d232e",
          line: "#103344",
          accent: "#22d3ee",
          warn: "#f59e0b",
          bull: "#16a34a",
          bear: "#dc2626"
        }
      },
      boxShadow: {
        glow: "0 0 25px rgba(34, 211, 238, 0.18)",
      },
      fontFamily: {
        mono: ["IBM Plex Mono", "monospace"],
      },
      keyframes: {
        riseIn: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        riseIn: "riseIn 450ms ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
