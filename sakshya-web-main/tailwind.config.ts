import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        clinical: {
          primary: "#0F766E",
          "primary-dark": "#115E59",
          "primary-soft": "#CCFBF1",
          "primary-container": "#99F6E4",
          secondary: "#0284C7",
          "secondary-soft": "#E0F2FE",
          danger: "#DC2626",
          "danger-dark": "#991B1B",
          "danger-soft": "#FEF2F2",
          "danger-container": "#FEE2E2",
          warning: "#D97706",
          "warning-soft": "#FFFBEB",
          success: "#0D9488",
          "success-soft": "#ECFDF5",
          canvas: "#F8FAFC",
          card: "#FFFFFF",
          border: "#CBD5E1",
          "border-subtle": "#E2E8F0",
          text: "#0F172A",
          "text-secondary": "#475569",
        },
        // Keep legacy color aliases intact so existing utilities never break
        brand: {
          50: "#F0FDFA",
          100: "#CCFBF1",
          200: "#99F6E4",
          400: "#2DD4BF",
          500: "#14B8A6",
          600: "#0D9488",
          700: "#0F766E",
          800: "#115E59",
          900: "#134E4A",
        },
        emergency: {
          50: "#FEF2F2",
          100: "#FEE2E2",
          500: "#EF4444",
          600: "#DC2626",
          700: "#B91C1C",
          800: "#991B1B",
          900: "#7F1D1D",
        },
        warning: {
          50: "#FFFBEB",
          100: "#FEF3C7",
          500: "#F59E0B",
          600: "#D97706",
          700: "#B45309",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-noto-sans)",
          "Noto Sans",
          "Noto Sans Devanagari",
          "Noto Sans Kannada",
          "Noto Sans Tamil",
          "system-ui",
          "sans-serif",
        ],
      },
      minHeight: {
        touch: "44px",
        "touch-lg": "56px",
      },
      minWidth: {
        touch: "44px",
      },
    },
  },
  plugins: [],
};

export default config;
