/**
 * Theme management utility - shared across all pages
 * Stores theme preference in localStorage
 */

export function getTheme() {
  const stored = localStorage.getItem('theme');
  if (stored) {
    return stored;
  }
  // Default to system preference
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function setTheme(theme) {
  localStorage.setItem('theme', theme);
  applyTheme(theme);
}

export function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

export function toggleTheme() {
  const currentTheme = getTheme();
  const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
  setTheme(newTheme);
  return newTheme;
}

// Initialize theme on page load
export function initTheme() {
  const theme = getTheme();
  applyTheme(theme);
  return theme;
}
