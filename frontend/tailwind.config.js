import tailwindcssAnimate from "tailwindcss-animate";

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        border: "rgba(148, 163, 184, 0.18)",
        background: "#020617",
        foreground: "#e5eefb",
        muted: "#94a3b8",
        accent: {
          DEFAULT: "#38bdf8",
          strong: "#0ea5e9",
          soft: "rgba(56, 189, 248, 0.12)"
        },
        panel: "rgba(15, 23, 42, 0.72)"
      },
      boxShadow: {
        glow: "0 0 38px rgba(14, 165, 233, 0.18)",
        panel: "0 18px 60px rgba(0, 0, 0, 0.28)"
      },
      borderRadius: {
        panel: "0.75rem"
      }
    }
  },
  plugins: [tailwindcssAnimate]
};
