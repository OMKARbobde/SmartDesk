/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        desk: {
          bg: '#0a0e16',
          surface: '#0f131c',
          container: '#181c24',
          highlight: '#202634',
          border: '#1e2638',
          subtle: '#2a3449',
          primary: '#3b82f6',
          primaryHover: '#2563eb',
          ai: '#8b5cf6',
          success: '#10b981',
          warning: '#f59e0b',
          danger: '#ef4444',
          muted: '#94a3b8',
          text: '#f1f5f9'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      borderRadius: {
        desk: '8px',
      },
      boxShadow: {
        'desk-glow': '0 0 20px -5px rgba(59, 130, 246, 0.15)',
        'desk-modal': '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
      }
    },
  },
  plugins: [],
}
