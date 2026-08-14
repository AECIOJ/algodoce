/** @type {import('tailwindcss').Config} */
// As cores do tema (cores de marca/neutras/feedback/apoio) vêm de
// `app/config.py` → `app/ajsystem/core/do_themes.py` → `tailwind.daisyui.json`.
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
    // Padrão: temas do host (tailwind.daisyui.json). O build do CSS pré-compilado
    // do framework (`npm run build:css:framework`) aponta via DAISYUI_THEMES para
    // `app/ajsystem/tailwind.daisyui.framework.json`.
    themes: require(process.env.DAISYUI_THEMES || './tailwind.daisyui.json'),
  },
  plugins: [require('daisyui')],
}
