/** @type {import('tailwindcss').Config} */
// As cores do tema (cores de marca/neutras/feedback/apoio) vêm de
// `app/config.py` → `scripts/gen_theme.py` → `tailwind.daisyui.json`.
// Não edite este arquivo para trocar cores; altere `Temas` em app/config.py
// e rode `npm run build:css`.
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
    themes: require('./tailwind.daisyui.json'),
  },
  plugins: [require('daisyui')],
}
