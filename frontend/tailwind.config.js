/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#19323a',
        muted: '#708188',
        accent: '#39796f',
        accentSoft: '#e7f2ee',
        canvas: '#f5f8f7',
        line: '#e3eae8',
      },
      boxShadow: {
        card: '0 12px 32px rgba(25, 50, 58, 0.055)',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
