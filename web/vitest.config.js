import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Use happy-dom for fast DOM simulation (no real browser needed)
    environment: 'happy-dom',

    // Test file patterns
    include: ['js/**/*.test.js'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      include: ['js/**/*.js'],
      exclude: [
        'js/**/*.test.js',
        'js/alpine-bootstrap.js', // Entry point, tested via E2E
      ],
    },

    // Fast execution
    globals: true,

    // Test output
    reporter: 'verbose',
  },
});
