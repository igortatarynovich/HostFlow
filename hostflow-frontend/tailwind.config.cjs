/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx,js,jsx,css}" // важно: чтобы подхватить components.css
  ],
  theme: {
    extend: {
      colors: {
        // ПАЛИТРА под фирменный бирюзовый (brand-500 ≈ #6BC6CF)
        brand: {
          50:  "#F1FBFD",
          100: "#E4F6F8",
          200: "#C7EDF0",
          300: "#A0DEE4",
          400: "#7FD0D6",
          500: "#6BC6CF",
          600: "#2BB4C1",
          700: "#1991A4",
          800: "#0F6E7D",
          900: "#0A5662"
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