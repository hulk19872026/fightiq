/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        dark: { 900: '#0a0a0a', 800: '#111111', 700: '#161616', 600: '#1e1e1e', 500: '#252525' },
        brand: { red: '#d32f2f', green: '#4ade80', yellow: '#ffd600', blue: '#42a5f5' },
      },
    },
  },
  plugins: [],
}
