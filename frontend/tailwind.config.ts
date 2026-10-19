import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          100: "#d9e6ff",
          500: "#3b6ef5",
          600: "#2f5be0",
          700: "#2749b8",
          900: "#1b2f73",
        },
      },
    },
  },
  plugins: [],
};

export default config;
