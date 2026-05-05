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
          50:  "#fff1f0",
          100: "#ffe1de",
          200: "#ffc8c2",
          300: "#ffa196",
          400: "#ff6b5b",
          500: "#f83a2a",
          600: "#e51e0e",
          700: "#c1160a",
          800: "#9f160d",
          900: "#831912",
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
