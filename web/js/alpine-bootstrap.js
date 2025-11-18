/**
 * Alpine.js Bootstrap
 * Loads Alpine from CDN, registers components, and starts the framework
 * Modern ES6 module approach for no-compile architecture
 */

import Alpine from 'https://cdn.jsdelivr.net/npm/alpinejs@3/dist/module.esm.js';
import Collapse from 'https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3/dist/module.esm.js';
import { simsApp } from './components/app.js?v=4';

// Make Alpine available globally for debugging
window.Alpine = Alpine;

// Register Alpine plugins
Alpine.plugin(Collapse);

// Register the simsApp component
Alpine.data('simsApp', simsApp);

// Start Alpine
Alpine.start();

console.log('✅ Alpine.js initialized with Collapse plugin and simsApp component');
