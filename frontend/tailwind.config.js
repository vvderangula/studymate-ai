/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Warm-white theme: soft ivory surfaces, warm charcoal text, orange
        // reserved for actions, active states and highlights.
        canvas: "#FBF8F5",
        surface: "#FFFFFF",
        sunken: "#F6F1EC",
        line: {
          DEFAULT: "#EEE5DD",
          strong: "#E2D5CA",
        },
        ink: {
          DEFAULT: "#1F1915", // 16.4:1 on canvas
          soft: "#4A3F38",
          hover: "#2A221D",
        },
        muted: "#75685F", // 5.1:1 on canvas
        faint: "#A99B90",
        accent: {
          // A thick, saturated orange.
          DEFAULT: "#EA580C", // indicators, rings, highlights
          light: "#F97316", // top of the button gradient
          strong: "#DD4C05", // primary buttons
          hover: "#C2410C",
          ink: "#A93A07", // orange text on soft tints
          soft: "#FFEEDF",
          tint: "#FFD9BA",
          line: "#FBBF8E",
        },
        danger: {
          DEFAULT: "#B42318",
          soft: "#FEF3F2",
          line: "#F7D2CE",
        },
        success: {
          DEFAULT: "#15803D",
          soft: "#F0FDF4",
        },
      },
      fontFamily: {
        sans: [
          "Geist",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
      },
      fontSize: {
        display: ["2rem", { lineHeight: "2.5rem", letterSpacing: "-0.025em", fontWeight: "600" }],
        title: ["1.375rem", { lineHeight: "2rem", letterSpacing: "-0.02em", fontWeight: "600" }],
      },
      borderRadius: {
        control: "8px",
        panel: "12px",
        card: "16px",
        bubble: "16px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(60, 40, 25, 0.04), 0 0 0 1px rgba(60, 40, 25, 0.02)",
        raised: "0 12px 32px -12px rgba(60, 40, 25, 0.14), 0 1px 2px rgba(60, 40, 25, 0.05)",
        focus: "0 0 0 3px rgba(249, 115, 22, 0.22)",
        pill: "0 1px 2px rgba(60, 40, 25, 0.08), 0 0 0 1px rgba(60, 40, 25, 0.04)",
      },
      maxWidth: {
        prose: "68ch",
        form: "26rem", // 416px
        reading: "45rem", // 720px
        page: "75rem", // 1200px
      },
    },
  },
  plugins: [],
};
