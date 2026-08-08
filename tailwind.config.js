/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/templates/**/*.html',
    './app/ajsystem/templates/**/*',
    './app/**/*.py',
  ],
  corePlugins: {
    preflight: false,
  },
  daisyui: {
    themes: [
      {
        algodoce: {
          "primary": "#26A69A",
          "primary-content": "#ffffff",
          "secondary": "#E91E63",
          "secondary-content": "#ffffff",
          "accent": "#FFB300",
          "neutral": "#37474F",
          "base-100": "#f5f5f5",
          "base-200": "#e0e0e0",
          "base-300": "#bdbdbd",
          "--fallback-bc": "#1f2937",
          "info": "#0288D1",
          "success": "#43A047",
          "success-content": "#FFFFFF",
          "warning": "#FB8C00",
          "error": "#E53935",
        },
      },
      "light",
      "dark",
    ],
  },
  plugins: [require('daisyui')],
}
