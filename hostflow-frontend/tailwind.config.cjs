/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx,js,jsx,css}" // важно: чтобы подхватить components.css
  ],
  theme: {
    extend: {
      colors: {
        // Brand tokens aligned to docs/pipedesign.md
        // Primary: #3FA3A8, Accent: #2E6F74, Section bg: #F4F8F9
        brand: {
          50:  "#F4F8F9",
          100: "#E6EEF0",
          200: "#CDE2E4",
          300: "#A7CED1",
          400: "#6FB3B8",
          500: "#3FA3A8",
          600: "#338B90",
          700: "#2E6F74",
          800: "#255A5E",
          900: "#1D4A4D"
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "Roboto", "Arial", "sans-serif"],
      },
      borderRadius: {
        xl: "0.75rem",
      },
      boxShadow: {
        sm: "0 1px 2px 0 rgb(16 24 40 / 0.06)",
        card: "0 6px 24px rgb(16 24 40 / 0.06)",
      },
    },
  },
  plugins: [],
};