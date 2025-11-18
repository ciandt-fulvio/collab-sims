# Sims Web Frontend

Modern web interface for monitoring and interacting with Sims agents in real-time.

## Stack

- **Alpine.js 3** - Reactive UI framework (15KB, no build step)
- **Tailwind CSS** - Utility-first CSS (via CDN)
- **Vanilla JavaScript** - ES Modules for clean architecture
- **Server-Sent Events (SSE)** - Real-time event streaming

## Features

- 🔄 Real-time session management
- 💬 Chat interface with streaming responses
- 🔤 Word-by-word text streaming (optional)
- ✅ **Tool approval workflow** - Approve/reject tool executions in real-time
- 🛠️ Tool call monitoring
- 📋 Task plan visualization
- 📊 Cost and token tracking
- 📝 Complete event log

## Development

### Quick Start

From project root:
```bash
./scripts/dev-server.sh
```

This automatically:
- Starts FastAPI server on `http://localhost:3004`
- Starts web frontend on `http://localhost:3005`
- Shows logs from both services

### Manual Start

**Terminal 1 - Backend:**
```bash
poetry run uvicorn sims.api.main:app --reload --port 3004
```

**Terminal 2 - Frontend:**
```bash
cd web
python3 -m http.server 3005
```

Then open: http://localhost:3005

## Usage

1. **Create Session** - Click "New Session" button
2. **Send Message** - Type in the input and press Send or Enter
3. **Watch Events** - Switch between Events/Tools/Approvals/Plan tabs to monitor

### Configuration

Toggle "Word-by-word" to enable/disable partial message streaming.

### Approval Workflow

The **Approvals** tab shows tools waiting for user approval before execution:

**Approval Modes:**
- `auto` - All tools execute automatically (no approvals needed)
- `interactive` - Only risky tools require approval (based on risk level)
- `manual` - Every tool requires approval

**When an approval is requested:**
1. UI automatically switches to Approvals tab
2. Red badge shows pending approval count
3. Approval card displays:
   - Tool name (e.g., "Bash", "Write", "Edit")
   - Risk level (safe/medium/high) - color coded
   - Tool input parameters

**Actions:**
- **Approve** - Execute tool once
- **Approve & Remember** - Execute and auto-approve this tool in future
- **Reject** - Skip tool execution with reason

**Testing Approvals:**

Create a session with manual approval mode:
```javascript
// In api.js or browser console
const response = await fetch('http://localhost:3004/api/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    config: {
      approval_config: {
        mode: 'manual',  // Requires approval for all tools
        tool_policies: {
          'Bash': 'high',
          'Write': 'medium',
          'Read': 'safe'
        },
        auto_approved_tools: []
      }
    }
  })
});
```

Then ask the agent to do something requiring tools (e.g., "create a file called hello.txt").

## Project Structure

```
web/
├── index.html              # Main HTML
├── js/
│   ├── components/
│   │   └── app.js         # Main Alpine component
│   └── services/
│       └── api.js         # API client & SSE handler
├── css/
│   └── styles.css         # Custom styles
└── README.md
```

## Key Features Explained

### Real-time Streaming

All events stream via SSE:
- `query` - Query started
- `partial_message` - Incremental text chunks
- `message` - Complete text response
- `tool_use` - Tool execution started
- `tool_result` - Tool execution completed
- `approval_request` - Tool requires approval (blocks until approved/rejected)
- `approval_response` - Approval decision made
- `plan` - Task list update
- `progress` - Progress update
- `complete` - Query finished with metrics

### Event Log

View all raw events in JSON format. Useful for:
- Debugging
- Understanding event flow
- Monitoring agent behavior

### Tool Monitoring

See all tool calls with:
- Tool name
- Input parameters
- Results (when available)
- Timestamps

### Plan Tracking

Visual progress bar and task list showing:
- Total tasks
- Completed tasks
- Current task status
- Task changes over time

## Deployment

### Static Hosting (Recommended)

Deploy to Vercel/Netlify/GitHub Pages:

1. Update `js/services/api.js`:
   ```javascript
   const API_BASE_URL = 'https://your-api-url.com';
   ```

2. Deploy `web/` folder:
   ```bash
   vercel deploy
   # or
   netlify deploy
   ```

### Bundle with FastAPI

Serve from same domain:

```python
# sims/api/main.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="web", html=True), name="web")
```

Then deploy as single service.

### Docker

```dockerfile
FROM python:3.11-slim
COPY . /app
WORKDIR /app
RUN pip install sims
EXPOSE 3004
CMD ["uvicorn", "sims.api.main:app", "--host", "0.0.0.0", "--port", "3004"]
```

## Browser Support

Modern browsers with support for:
- ES6 Modules
- Fetch API
- ReadableStream
- CSS Grid/Flexbox

Tested on:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## No Build Step

This is intentional! Benefits:
- Instant refresh during development
- No node_modules
- No build configuration
- Easy to understand and modify
- Deploy anywhere

If you need bundling later, add Vite:
```bash
npm create vite@latest . -- --template vanilla
```

Your code will work as-is.

## Troubleshooting

**CORS errors:**
- Check FastAPI CORS middleware in `sims/api/main.py`
- Ensure frontend origin is in `allow_origins`

**Events not streaming:**
- Check browser console for errors
- Verify backend is running on port 3004
- Check network tab for SSE connection

**Session not creating:**
- Verify backend is accessible
- Check `/api/sessions` endpoint in browser
- Review server logs for errors

## Contributing

This is a simple, vanilla setup. Feel free to:
- Add new components
- Enhance styling
- Add features
- Improve error handling

Keep it simple and avoid over-engineering!
