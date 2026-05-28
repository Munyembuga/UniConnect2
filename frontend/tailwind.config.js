/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00628b',
          dark:    '#00587d',
          light:   '#30a1c6',
          50:      '#e6f4f9',
          100:     '#b3ddef',
          200:     '#80c6e4',
        },
        slate: {
          ur:   '#364f68',
          dark: '#323e43',
        },
        gold: {
          DEFAULT: '#e8a800',
          light:   '#f5c842',
        },
      },
      fontFamily: {
        sans: ['Montserrat', 'Open Sans', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'hero-gradient': 'linear-gradient(135deg, #00628b 0%, #364f68 60%, #323e43 100%)',
        'section-gradient': 'linear-gradient(180deg, #00587d 0%, #364f68 100%)',
      },
      boxShadow: {
        'card': '0 2px 16px 0 rgba(0,98,139,0.10)',
        'card-hover': '0 6px 28px 0 rgba(0,98,139,0.18)',
      },
    },
  },
  plugins: [],
}
