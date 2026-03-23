/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // 阳光书房配色系统 (Amber Glow)
        cream: {
          DEFAULT: '#FDF8F3',
          light: '#FEFCF9',
        },
        warm: {
          50: '#FDF8F3',
          100: '#F5EDE4',
          200: '#E8D5C4',
          300: '#D4A574',
          400: '#C49464',
          500: '#8B6914',
          600: '#6B500F',
        },
        ink: {
          DEFAULT: '#2C2416',
          light: '#4A3F2E',
        },
        muted: {
          DEFAULT: '#6B5B4F',
          light: '#8B7B6F',
        },
        moss: {
          DEFAULT: '#7A9E7E',
          light: '#9ABE9E',
          dark: '#5A7E5E',
        },
        brick: {
          DEFAULT: '#B85450',
          light: '#D47470',
        },
        // 保留兼容性别名
        ember: '#D4A574',
        pine: '#7A9E7E',
        mist: '#F5EDE4',
      },
      fontFamily: {
        display: ['Cormorant Garamond', 'Georgia', 'Times New Roman', 'serif'],
        body: ['Source Sans 3', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        code: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        panel: '0 4px 24px rgba(44, 36, 22, 0.08)',
        'panel-lg': '0 8px 40px rgba(44, 36, 22, 0.12)',
        soft: '0 2px 12px rgba(139, 105, 20, 0.06)',
        glow: '0 0 20px rgba(212, 165, 116, 0.3)',
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '24px',
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'slide-in-left': 'slideInLeft 300ms ease-out',
        'slide-in-right': 'slideInRight 300ms ease-out',
        'fade-in': 'fadeIn 200ms ease-out',
      },
      keyframes: {
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        slideInLeft: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
