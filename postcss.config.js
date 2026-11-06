module.exports = {
  plugins: {
    // `@import` primeiro: resolve Tailwind e os CSS locais em um único arquivo
    // antes de o Tailwind gerar as utilities.
    'postcss-import': {},
    tailwindcss: {},
    autoprefixer: {},
  },
}
