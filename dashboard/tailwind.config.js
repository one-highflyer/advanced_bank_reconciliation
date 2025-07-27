/** @type {import('tailwindcss').Config} */
import animate from 'tailwindcss-animate';

export default {
  darkMode: ['class'],
  content: ["./src/**/*.{html,jsx,tsx,vue,js,ts}"],
  theme: {
    extend: {
      borderRadius: {
        lg: '0.5rem',
        md: '0.375rem',
        sm: '0.25rem'
      },
      height: {
        '144': '36rem', // 576px
        '128': '32rem', // 512px
      },
      maxHeight: {
        '144': '36rem', // 576px
        '128': '32rem', // 512px
      }
    },
  },
  plugins: [
    animate
  ],
}

