/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Azeon Systems brand tokens — see CLAUDE.md
        "azeon-orange": {
          DEFAULT: "#F57C00", // Primary — high energy, primary actions
          dark: "#C96500", // hover/active state
        },
        "azeon-navy": {
          DEFAULT: "#0D47A1", // Secondary — professional, headers/navbars
          dark: "#093275",
        },
        "azeon-white": "#FFFFFF",
        "azeon-gray": "#9E9E9E",
      },
      fontFamily: {
        // Bound to CSS vars emitted by next/font/google in app/layout.tsx
        heading: ["var(--font-montserrat)", "Helvetica Neue", "Arial", "sans-serif"],
        body: ["var(--font-open-sans)", "Helvetica Neue", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [],
};
