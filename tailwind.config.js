/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/templates/**/*.html',
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
          "info": "#0288D1",
          "success": "#43A047",
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
