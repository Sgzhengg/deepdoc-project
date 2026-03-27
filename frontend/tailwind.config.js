/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./index-mobile.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        chat: {
          bg: '#343541',
          'bg-secondary': '#444654',
          input: '#40414f',
          text: '#ececf1',
          border: '#565869',
          accent: '#10a37f',
          'user-bubble': '#343541',
          'ai-bubble': '#444654',
        },
      },
      width: {
        'sidebar': '260px',
        'panel': '280px',
      },
    },
  },
  plugins: [],
}
