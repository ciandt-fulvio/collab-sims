# Sims Frontend Architecture

Modern ES6 module-based architecture with no build step required.

## Structure

```
web/js/
├── alpine-bootstrap.js       # Entry point - loads Alpine.js and registers components
├── components/
│   ├── app.js                # Main Alpine.js component (506 lines, down from 712)
│   ├── chat/                 # Chat-specific components
│   │   ├── metricsPanel.js   # Metrics tracking (98 lines)
│   │   ├── planPanel.js      # Plan/todos display (49 lines)
│   │   ├── eventsPanel.js    # Events list and filtering (79 lines)
│   │   └── approvalsPanel.js # Approval requests (83 lines)
│   ├── sessions/             # Sessions-specific components (future)
│   └── shared/               # Shared components (future)
├── services/
│   └── api.js                # API client and SSE stream handler
├── handlers/
│   └── eventHandlers.js      # Event routing and handlers
├── state/
│   └── sessionState.js       # State management utilities
└── utils/
    ├── rendering.js          # Markdown, HTML escaping, event summaries
    └── toolFormatters.js     # Tool input/output formatters
```

## Key Features

### ✅ Modern ES6 Modules
- No build step required - runs directly in browsers
- Clean import/export syntax
- Alpine.js loaded from CDN via ESM build

### ✅ Separation of Concerns
- **Components**: Alpine.js reactive UI components
- **Services**: API communication and SSE streaming
- **Handlers**: Event processing logic
- **State**: State initialization and management
- **Utils**: Pure functions for formatting and rendering

### ✅ Modular Architecture
- Original monolithic `app.js` (712 lines) reduced to 506 lines (29% reduction)
- Chat components extracted into focused sub-components (49-98 lines each)
- Logic distributed across specialized, testable modules
- Each module has a single responsibility

## How It Works

### 1. Module Loading (alpine-bootstrap.js)
```javascript
import Alpine from 'https://cdn.jsdelivr.net/npm/alpinejs@3/dist/module.esm.js';
import { simsApp } from './components/app.js';

Alpine.data('simsApp', simsApp);
Alpine.start();
```

### 2. Component Composition
The `simsApp` function uses composition to combine sub-components:
```javascript
// app.js
import { metricsPanel } from './chat/metricsPanel.js';
import { planPanel } from './chat/planPanel.js';
import { eventsPanel } from './chat/eventsPanel.js';
import { approvalsPanel } from './chat/approvalsPanel.js';

export function simsApp() {
  return {
    ...metricsPanel(),    // Metrics tracking
    ...planPanel(),       // Plan/todos display
    ...eventsPanel(),     // Events list and filtering
    ...approvalsPanel(),  // Approval requests
    // ... other state and methods
  };
}
```

The composed component is registered with Alpine.js:
```html
<div x-data="simsApp()">
  <!-- Alpine.js bindings work here -->
</div>
```

### 3. Event Flow
```
SSE Stream → API Service → Event Handlers → State Updates → UI Updates
```

## Benefits

### 🚀 Performance
- No build step = instant development iteration
- Modules load in parallel via browser's native module loader
- Efficient caching via HTTP

### 🧪 Testability
- Pure functions in utils can be unit tested easily
- Event handlers are isolated and testable
- State management is separate from UI logic

### 📦 Maintainability
- Clear module boundaries
- Easy to locate functionality
- Simple to add new features

### 🔧 Developer Experience
- No transpilation or bundling needed
- Works with simple Python HTTP server
- Standard ES6 - no custom tooling

## Adding New Features

### Add a new chat panel component:
1. Create file in `components/chat/newPanel.js`
2. Export function that returns state and methods
3. Import and spread into `simsApp()` in `app.js`
4. Component gets composed into main app state

### Add a new tool formatter:
1. Add formatter to `utils/toolFormatters.js`
2. Export it from the module
3. Use it in component via import

### Add a new event type:
1. Create handler in `handlers/eventHandlers.js`
2. Add to event type map in `dispatchEvent()`
3. Handler receives component context and event

### Add new state:
1. Add to `createSessionState()` in `state/sessionState.js`
2. Create helper functions for accessing/updating
3. Import and use in component

## Browser Compatibility

Requires modern browsers with ES6 module support:
- Chrome 61+
- Firefox 60+
- Safari 11+
- Edge 16+

## Production Considerations

For production, consider:
- Using a CDN with proper caching headers
- Serving modules with compression (gzip/brotli)
- Optional: Bundle modules for older browsers (Vite/esbuild)
- Replace Tailwind CDN with compiled CSS

## Development

Start the dev server:
```bash
./scripts/dev-server.sh
```

Access at: http://localhost:3005

No watch/rebuild needed - just refresh the browser!
