/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#03000a",
          dark: "#080313",
          card: "rgba(13, 7, 28, 0.45)",
          blue: "#00f0ff",
          purple: "#d946ef",
          indigo: "#8b5cf6",
          gray: "#94a3b8",
          border: "rgba(217, 70, 239, 0.2)"
        }
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        display: ["var(--font-orbitron)", "monospace"]
      },
      backgroundImage: {
        "neon-gradient": "linear-gradient(135deg, #00f0ff 0%, #8b5cf6 50%, #d946ef 100%)",
        "cyber-grid": "linear-gradient(rgba(18, 10, 36, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(18, 10, 36, 0.3) 1px, transparent 1px)"
      },
      boxShadow: {
        "neon-blue": "0 0 15px rgba(0, 240, 255, 0.35)",
        "neon-purple": "0 0 15px rgba(217, 70, 239, 0.35)",
        "neon-glass": "inset 0 1px 1px rgba(255, 255, 255, 0.05), 0 8px 32px 0 rgba(0, 0, 0, 0.37)"
      },
      animation: {
        "spin-slow": "spin 20s linear infinite",
        "pulse-slow": "pulse 6s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float": "float 6s ease-in-out infinite"
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" }
        }
      }
    },
  },
  plugins: [],
}
