import type { Config } from "tailwindcss";

// Token 公园视觉色板（华为红色系，参考 FT 米粉色版面）
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 主背景：暖粉米
        canvas: "#FDF2EE",
        // 卡片 / 次背景：淡米粉红
        surface: "#F8E1DA",
        // 主文字：深棕红黑
        ink: "#3A1C1C",
        // 主色：中等华为红衍生
        accent: {
          DEFAULT: "#C9302C",
          strong: "#8B1A2E",
        },
        border: {
          DEFAULT: "#E8C9BF",
        },
        muted: "#7A5454",
      },
      fontFamily: {
        // 中文优先思源宋体 / 苹方，西文优先 Inter
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "PingFang SC",
          "Hiragino Sans GB",
          "Microsoft YaHei",
          "sans-serif",
        ],
        serif: [
          "Source Han Serif SC",
          "Songti SC",
          "STSong",
          "serif",
        ],
        mono: [
          "JetBrains Mono",
          "IBM Plex Mono",
          "ui-monospace",
          "Menlo",
          "monospace",
        ],
      },
      maxWidth: {
        prose: "70ch",
      },
    },
  },
  plugins: [],
};

export default config;
