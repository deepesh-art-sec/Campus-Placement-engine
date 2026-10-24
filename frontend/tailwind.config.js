/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#064e3b",
          900: "#022c22",
        },
        navy: {
          700: "#1b2b4d",
          800: "#111d38",
          850: "#0d1527",
          900: "#080e1c",
          950: "#060b14",
        },
        accent: {
          blue: "#2563eb",
          emerald: "#10b981",
          teal: "#0d9488",
        },
      },
      boxShadow: {
        "emerald-glow": "0 0 20px -3px rgba(16, 185, 129, 0.35)",
        "blue-glow": "0 0 20px -3px rgba(37, 99, 235, 0.35)",
        "card-dark": "0 4px 20px -2px rgba(2, 6, 23, 0.7)",
      },
    },
  },
  plugins: [],
}
