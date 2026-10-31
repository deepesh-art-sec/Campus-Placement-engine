/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        corporate: {
          navy: "#0B1F44",
          "navy-dark": "#071530",
          "navy-light": "#152B58",
          blue: "#2563EB",
          "blue-hover": "#1D4ED8",
          "blue-light": "#EFF6FF",
          canvas: "#F8FAFC",
          card: "#FFFFFF",
          border: "#E2E8F0",
        },
        navy: {
          700: "#1E3A8A",
          800: "#132B5B",
          850: "#0F234B",
          900: "#0B1F44",
          950: "#071530",
        },
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        accent: {
          blue: "#2563EB",
          emerald: "#10B981",
          teal: "#0D9488",
          amber: "#F59E0B",
          rose: "#EF4444",
        },
      },
      fontFamily: {
        sans: ["'Inter'", "sans-serif"],
      },
      boxShadow: {
        "subtle": "0 1px 3px 0 rgba(15, 23, 42, 0.05), 0 1px 2px -1px rgba(15, 23, 42, 0.03)",
        "card": "0 2px 6px -1px rgba(15, 23, 42, 0.06), 0 1px 4px -2px rgba(15, 23, 42, 0.04)",
        "card-hover": "0 10px 25px -3px rgba(15, 23, 42, 0.08), 0 4px 10px -4px rgba(15, 23, 42, 0.04)",
        "blue-glow": "0 0 20px -3px rgba(37, 99, 235, 0.25)",
      },
    },
  },
  plugins: [],
}
