/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // RGB-triplet pattern so we can swap accents via CSS vars at runtime.
        bgp: 'rgb(var(--bg-primary) / <alpha-value>)',
        bgs: 'rgb(var(--bg-surface) / <alpha-value>)',
        bgs2: 'rgb(var(--bg-surface-2) / <alpha-value>)',
        ink: 'rgb(var(--text-primary) / <alpha-value>)',
        inkm: 'rgb(var(--text-muted) / <alpha-value>)',
        bordr: 'rgb(var(--border) / <alpha-value>)',

        brand: 'rgb(var(--brand) / <alpha-value>)',
        'brand-hover': 'rgb(var(--brand-hover) / <alpha-value>)',

        shop: 'rgb(var(--shop-accent) / <alpha-value>)',
        events: 'rgb(var(--events-accent) / <alpha-value>)',
        services: 'rgb(var(--services-accent) / <alpha-value>)',
        creators: 'rgb(var(--creators-accent) / <alpha-value>)',

        success: 'rgb(var(--success) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        danger: 'rgb(var(--danger) / <alpha-value>)',
      },
      fontFamily: {
        body: ['Inter', 'system-ui', 'sans-serif'],
        display: ['"Cormorant Garamond"', 'Georgia', 'serif'],
      },
      boxShadow: {
        'inner-line': 'inset 0 0 0 1px rgb(var(--border) / 1)',
        glow: '0 0 60px -20px rgb(var(--brand) / 0.6)',
      },
      backgroundImage: {
        'grain':
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' /%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.3'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
};
