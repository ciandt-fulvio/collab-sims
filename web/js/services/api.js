/**
 * API service for Sims agent communication
 * ES6 module - no build step required
 */

// API configuration
const API_BASE_URL = window.location.hostname === 'localhost'
  ? 'http://localhost:3007'
  : 'https://api.yourapp.com';

// API service
export class SimsAPI {
  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  async createSession(config = {}, sessionType = 'worker') {
    const response = await fetch(`${this.baseURL}/api/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ config, session_type: sessionType }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.statusText}`);
    }

    return await response.json();
  }

  async querySession(sessionId, prompt) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) {
      throw new Error(`Failed to query session: ${response.statusText}`);
    }

    return await response.json();
  }

  createEventStream(sessionId, prompt) {
    return new EventStreamHandler(`${this.baseURL}/api/sessions/${sessionId}/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });
  }

  async listSessions() {
    const response = await fetch(`${this.baseURL}/api/sessions`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to list sessions: ${response.statusText}`);
    }

    return await response.json();
  }

  async getSession(sessionId) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get session: ${response.statusText}`);
    }

    return await response.json();
  }

  async getSessionEvents(sessionId, page = 1, pageSize = 100, eventType = null) {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (eventType) {
      params.append('event_type', eventType);
    }

    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/events?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get session events: ${response.statusText}`);
    }

    return await response.json();
  }

  async deleteSession(sessionId) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to delete session: ${response.statusText}`);
    }
  }

  async interruptSession(sessionId) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/interrupt`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to interrupt session: ${response.statusText}`);
    }

    return await response.json();
  }

  async getPendingApprovals(sessionId) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/approvals/pending`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get pending approvals: ${response.statusText}`);
    }

    return await response.json();
  }

  async respondToApproval(sessionId, toolUseId, approved, remember = false, reason = null) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/approvals/${toolUseId}/respond`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ approved, remember, reason }),
    });

    if (!response.ok) {
      throw new Error(`Failed to respond to approval: ${response.statusText}`);
    }

    return await response.json();
  }

  async getApprovalConfig(sessionId) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/approvals/config`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get approval config: ${response.statusText}`);
    }

    return await response.json();
  }

  async updateApprovalConfig(sessionId, config) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/approvals/config`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      throw new Error(`Failed to update approval config: ${response.statusText}`);
    }

    return await response.json();
  }
}

// EventSource handler for SSE streaming
export class EventStreamHandler {
  constructor(url, options) {
    this.url = url;
    this.options = options;
    this.handlers = {};
    this.eventSource = null;
  }

  async start() {
    // For POST requests with body, we need to use fetch + ReadableStream
    const response = await fetch(this.url, this.options);

    if (!response.ok) {
      throw new Error(`Stream failed: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const readChunk = async () => {
      const { done, value } = await reader.read();

      if (done) {
        this.emit('end');
        return;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.substring(6);
          if (data.trim()) {
            try {
              const event = JSON.parse(data);
              this.emit('message', event);
              this.emit(event.type || event.event_type, event);
            } catch (e) {
              console.error('Failed to parse SSE data:', data, e);
            }
          }
        }
      }

      readChunk();
    };

    readChunk().catch(error => {
      this.emit('error', error);
    });
  }

  on(eventType, handler) {
    if (!this.handlers[eventType]) {
      this.handlers[eventType] = [];
    }
    this.handlers[eventType].push(handler);
    return this;
  }

  emit(eventType, data) {
    const handlers = this.handlers[eventType] || [];
    handlers.forEach(handler => handler(data));

    // Also call wildcard handlers
    const wildcardHandlers = this.handlers['*'] || [];
    wildcardHandlers.forEach(handler => handler(eventType, data));
  }

  close() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  }
}
