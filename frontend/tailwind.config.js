/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "hsl(0 0% 98%)",
          100: "hsl(0 0% 95%)",
          200: "hsl(0 0% 85%)",
          300: "hsl(0 0% 70%)",
          400: "hsl(0 0% 55%)",
          500: "hsl(0 0% 40%)",
          600: "hsl(0 0% 28%)",
          700: "hsl(0 0% 18%)",
          800: "hsl(0 0% 11%)",
          900: "hsl(0 0% 6%)",
          950: "hsl(0 0% 3%)",
        },
      },
      fontFamily: {
        sans: ["Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["\"Source Serif 4\"", "ui-serif", "Georgia", "serif"],
      },
      borderRadius: {
        DEFAULT: "1rem",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.7s ease-out both",
        "fade-in": "fade-in 0.9s ease-out both",
      },
    },
  },
  plugins: [],
};
