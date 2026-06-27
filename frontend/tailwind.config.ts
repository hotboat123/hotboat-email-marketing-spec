import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#f0faf9",
          100: "#d6f0ee",
          200: "#aedfdb",
          300: "#7eccc5",
          400: "#5fb8ae",
          500: "#47a49a",
          600: "#34897f",
          700: "#2c7a72",
          800: "#246b64",
          900: "#235e58",
        },
        accent: {
          DEFAULT: "#c98a3c",
          light:   "#e0a85a",
          dark:    "#a86d28",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
