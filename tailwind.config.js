/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./templates/**/*.{html,js}"],
    theme: {
      extend: {},
    },
    plugins: [require('@tailwindcss/typography'),require('daisyui')],
    daisyui: {themes: ['light','dark','cupcake','halloween','emerald']}
  }