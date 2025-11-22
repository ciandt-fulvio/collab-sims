/**
 * Main Alpine.js component
 * Refactored to use modular imports for maintainability
 */

import { SimsAPI } from '../services/api.js?v=4';
import { formatToolInput, formatToolOutput } from '../utils/toolFormatters.js?v=4';
import { escapeHtml, renderMarkdown, getEventSummary } from '../utils/rendering.js?v=4';
import { dispatchEvent } from '../handlers/eventHandlers.js?v=4';
import {
  getCurrentToolGroup,
  getToolGroup
} from '../state/sessionState.js?v=4';
import { initTheme, toggleTheme as toggleThemeUtil } from '../utils/theme.js?v=4';
import { metricsPanel } from './chat/metricsPanel.js?v=4';
import { planPanel } from './chat/planPanel.js?v=4';
import { eventsPanel } from './chat/eventsPanel.js?v=4';

export function simsApp() {
  return {
    // API client
    api: new SimsAPI(),

    // Session state
    sessionId: null,
    sessionRole: null,  // 'worker' or 'scout'
    agentName: null,    // agent name if this is a swarm agent session
    swarmId: null,      // swarm ID if this is a swarm agent session
    isStreaming: false,
    isInitializing: true,
    _initCalled: false,  // Guard flag to prevent double initialization
    isLoadingHistory: false,  // Flag to distinguish history load from live streaming
    isRestoringSession: false,  // Flag for showing skeleton UI during session load

    // Theme state (light, dark, or system) - managed by theme utility
    theme: initTheme(),


    // UI state
    activeTab: 'plan',
    prompt: '',
    partialText: '',
    sessionType: 'worker', // Session type: worker or scout

    // Data
    messages: [],

    // Dropdown visibility states
    showSessionTypeDropdown: false,

    // Component composition
    ...metricsPanel(),
    ...planPanel(),
    ...eventsPanel(),

    // Track seen message events to prevent duplicates
    seenMessages: new Set(),

    // Track seen event IDs to prevent duplicates (all event types)
    seenEventIds: new Set(),

    // Track tool executions grouped by turn
    toolGroups: [], // Array of { id, messageId, tools: [{use, result}], timestamp, expanded }
    currentToolGroupId: null, // ID of the current tool group being populated

    // Initialize
    async init() {
      console.log('🔵 Sims Agent init() called');
      console.trace('init() call stack');

      // Guard against double initialization (Alpine.js bug)
      if (this._initCalled) {
        console.warn('⚠️ init() already called, skipping duplicate initialization');
        return;
      }
      this._initCalled = true;

      // Check if session ID is provided in URL (support both 'id' and 'session' params)
      const params = new URLSearchParams(window.location.search);
      const sessionIdFromUrl = params.get('id') || params.get('session');

      if (sessionIdFromUrl) {
        // Load existing session
        await this.loadSession(sessionIdFromUrl);
        this.isInitializing = false;
      } else {
        // No session ID - create a new session
        await this.createSession();
        this.isInitializing = false;
      }
    },

    // Create new session
    async createSession() {
      console.log('🟡 createSession() called');
      console.trace('createSession() call stack');

      try {
        // Clear existing state
        this.messages = [];
        this.resetEvents();
        this.resetPlans();
        this.resetApprovals();
        this.partialText = '';
        this.seenEventIds.clear();

        // Reset metrics
        this.metrics = {
          inputTokens: 0,
          outputTokens: 0,
          totalTokens: 0,
          totalCost: 0,
          durationMs: 0,
          numTurns: 0,
          messagesCount: 0,
          toolsCount: 0,
        };

        // Reset accumulated metrics
        this.accumulatedDurationMs = 0;
        this.accumulatedInputTokens = 0;
        this.accumulatedOutputTokens = 0;
        this.currentQueryInputTokens = 0;
        this.currentQueryOutputTokens = 0;

        console.log('🔵 Making API call to create session with type:', this.sessionType);
        const response = await this.api.createSession({
          include_partial_messages: true,  // Always enable word-by-word streaming
          approval_config: {
            mode: this.approvalMode,  // Use current approval mode
            tool_policies: {
              'Bash': 'high',
              'Write': 'medium',
              'Edit': 'medium',
              'Read': 'safe',
              'Glob': 'safe',
              'Grep': 'safe',
            },
            auto_approved_tools: []
          }
        }, this.sessionType);

        this.sessionId = response.session_id;
        this.sessionRole = this.sessionType;  // Store the role
        console.log('🟢 Session created:', this.sessionId, 'Role:', this.sessionRole);

        // Focus input field after session is ready
        this.focusInput();
      } catch (error) {
        console.error('🔴 Failed to create session:', error);
        alert('Failed to create session. Is the server running?');
      }
    },

    // Load existing session
    async loadSession(sessionId) {
      console.log('🟡 loadSession() called for:', sessionId);

      // Show skeleton loading UI
      this.isRestoringSession = true;

      try {
        // Clear existing state
        this.messages = [];
        this.resetEvents();
        this.resetPlans();
        this.resetApprovals();
        this.partialText = '';
        this.toolGroups = [];
        this.currentToolGroupId = null;
        this.seenMessages.clear();
        this.seenEventIds.clear();

        // Reset metrics
        this.metrics = {
          inputTokens: 0,
          outputTokens: 0,
          totalTokens: 0,
          totalCost: 0,
          durationMs: 0,
          numTurns: 0,
          messagesCount: 0,
          toolsCount: 0,
        };

        // Reset accumulated metrics
        this.accumulatedDurationMs = 0;
        this.accumulatedInputTokens = 0;
        this.accumulatedOutputTokens = 0;
        this.currentQueryInputTokens = 0;
        this.currentQueryOutputTokens = 0;

        // Set session ID
        this.sessionId = sessionId;

        // Load session details
        console.log('🔵 Loading session details...');
        const session = await this.api.getSession(sessionId);
        this.sessionRole = session.role;  // Store the role from loaded session
        this.agentName = session.agent_name || null;
        this.swarmId = session.swarm_id || null;
        console.log('🟢 Session loaded:', session);

        // Load all events from the session
        console.log('🔵 Loading session events...');
        const eventsResponse = await this.api.getSessionEvents(sessionId, 1, 1000);
        const events = eventsResponse.events || [];
        console.log('🟢 Loaded', events.length, 'events');

        // Set flag to indicate we're loading history (not live streaming)
        this.isLoadingHistory = true;

        // Process events to rebuild state
        for (let i = 0; i < events.length; i++) {
          const event = events[i];
          // Normalize event type field - DB uses event_type, UI expects type
          const eventType = event.event_type || event.type;

          // Events from database have nested 'data' field, live events don't
          // Flatten the structure for both display and processing
          const eventData = event.data || {};
          const { data, ...eventWithoutData } = event;  // Remove data field
          const normalizedEvent = {
            ...eventData,         // Spread data fields first
            ...eventWithoutData,  // Then spread top-level fields (without data)
            type: eventType,      // Ensure type is set
            event_type: eventType,
            // Generate truly unique ID by including index to prevent collisions
            id: event.id || event.event_id || `${eventType}-${event.timestamp}-${i}`
          };

          // Add normalized event to events array for display
          this.events.push(normalizedEvent);

          // Use dispatchEvent to process events and rebuild state
          // This ensures tool groups, plans, etc. are properly reconstructed
          dispatchEvent(this, normalizedEvent);
        }

        // Clear history loading flag
        this.isLoadingHistory = false;

        console.log('🟢 Session state restored');

        // Hide skeleton UI - session is fully loaded
        this.isRestoringSession = false;

        // Check if session has an active query (has QueryEvent but no CompleteEvent after it)
        const hasQueryEvent = events.some(e => e.type === 'query' || e.event_type === 'query');
        const lastEvent = events[events.length - 1];
        const lastEventIsComplete = lastEvent && (lastEvent.event_type === 'complete' || lastEvent.type === 'complete');
        const isStillStreaming = hasQueryEvent && !lastEventIsComplete;

        if (isStillStreaming) {
          console.log('🔵 Session has active query, reconnecting...');
          // Set streaming state so arrows show
          this.isStreaming = true;
          // Reconnect to ongoing SSE stream
          this.reconnectToActiveSession();
        } else if (!hasQueryEvent) {
          console.log('🟢 Session is empty (no queries sent yet)');
        } else {
          console.log('🟢 Session is complete');
        }

        // Focus input field
        this.focusInput();
      } catch (error) {
        console.error('🔴 Failed to load session:', error);
        this.isRestoringSession = false;  // Hide skeleton on error
        alert('Failed to load session: ' + error.message);
        // Fall back to creating a new session
        await this.createSession();
      }
    },

    // Send message
    async sendMessage() {
      if (!this.prompt.trim() || !this.sessionId) return;

      const userPrompt = this.prompt;
      this.prompt = '';

      // Add user message
      this.addMessage('user', userPrompt);

      // Start streaming
      this.isStreaming = true;
      this.partialText = '';
      this.seenMessages.clear(); // Clear seen messages for new query

      // Start real-time metrics tracking
      this.startDurationTimer();
      this.metrics.numTurns++;
      this.isMetricsLive = true;

      try {
        const stream = this.api.createEventStream(this.sessionId, userPrompt);

        stream
          .on('message', (event) => this.handleEvent(event))
          .on('error', (error) => {
            console.error('Stream error:', error);
            this.isStreaming = false;
            this.stopDurationTimer();
          })
          .on('end', () => {
            this.isStreaming = false;
          });

        await stream.start();
      } catch (error) {
        console.error('Failed to send message:', error);
        this.isStreaming = false;
        this.stopDurationTimer();
        alert('Failed to send message. Check console for details.');
      }
    },

    // Handle incoming events
    handleEvent(event) {
      // Use server-provided event_id, or generate fallback for legacy events
      const eventId = event.event_id || `${event.type}-${Date.now()}-${Math.random()}`;

      // Deduplicate ALL events by event_id to prevent duplicates
      if (this.seenEventIds.has(eventId)) {
        console.log('Skipping duplicate event:', eventId, event.type);
        return; // Skip entirely - don't add to events log or process further
      }
      this.seenEventIds.add(eventId);

      // Additional deduplication for message events (legacy, but kept for safety)
      if (event.type === 'message' || event.event_type === 'message') {
        const messageKey = `${event.content}:${event.timestamp}`;
        if (this.seenMessages.has(messageKey)) {
          console.log('Skipping duplicate message event (legacy check):', messageKey);
          return;
        }
        this.seenMessages.add(messageKey);
      }

      const eventWithId = {
        ...event,
        id: eventId,
      };
      this.events.push(eventWithId);

      // Keep only last 200 events
      if (this.events.length > 200) {
        this.events = this.events.slice(-200);
      }

      // Delegate to imported event handler
      dispatchEvent(this, event);
    },

    // Add message to chat
    addMessage(role, content, thinking = null, timestamp = null, eventId = null) {
      const message = {
        id: `${role}-${Date.now()}-${Math.random()}`,
        role,
        content,
        thinking,
        timestamp: timestamp || new Date().toISOString(),
        event_id: eventId, // Store event_id to link with tools
      };
      this.messages.push(message);
      this.scrollToBottom();
      return message;
    },

    // Approve a tool
    async approveApproval(toolUseId, remember = false) {
      try {
        await this.api.respondToApproval(this.sessionId, toolUseId, true, remember, null);
        console.log('Approval sent:', toolUseId);
      } catch (error) {
        console.error('Failed to approve:', error);
        alert('Failed to approve. Check console for details.');
      }
    },

    // Reject a tool
    async rejectApproval(toolUseId, reason = null) {
      try {
        await this.api.respondToApproval(this.sessionId, toolUseId, false, false, reason);
        console.log('Rejection sent:', toolUseId);
      } catch (error) {
        console.error('Failed to reject:', error);
        alert('Failed to reject. Check console for details.');
      }
    },

    // Interrupt current query
    async interruptSession() {
      if (!this.sessionId || !this.isStreaming) {
        console.warn('Cannot interrupt: no session or not streaming');
        return;
      }

      try {
        console.log('🛑 Interrupting session:', this.sessionId);
        const response = await this.api.interruptSession(this.sessionId);
        console.log('✅ Session interrupted:', response);
        this.isStreaming = false;
        this.stopDurationTimer();
        this.addMessage('system', '⏹️ Query interrupted by user');
      } catch (error) {
        console.error('Failed to interrupt session:', error);
        alert('Failed to interrupt. Check console for details.');
      }
    },

    // Get current plan (most recent)
    // State helper methods - delegate to imported functions
    getCurrentToolGroup() {
      return getCurrentToolGroup(this);
    },

    // Get compact event summary
    // Delegate to imported rendering utilities
    getEventSummary,  // Direct assignment from import
    escapeHtml,       // Direct assignment from import

    // Render markdown to HTML (wraps imported function + adds Alpine-specific post-processing)
    renderMarkdown(text) {
      const html = renderMarkdown(text);

      // Apply syntax highlighting to any code blocks that weren't caught
      this.$nextTick(() => {
        document.querySelectorAll('.markdown-content pre code:not(.hljs)').forEach((block) => {
          hljs.highlightElement(block);
        });
      });

      return html;
    },

    // Toggle theme
    toggleTheme() {
      this.theme = toggleThemeUtil();
    },

    // Truncate ID to first 8 characters
    truncateId(id) {
      if (!id) return '';
      return id.substring(0, 8);
    },

    // Copy ID to clipboard
    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
        console.log('Copied to clipboard:', text);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    },

    // Focus input field
    focusInput() {
      this.$nextTick(() => {
        const input = this.$refs.promptInput;
        if (input && !input.disabled) {
          input.focus();
        }
      });
    },

    // Scroll to bottom
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    },

    // Get tool group by ID
    getToolGroup(groupId) {
      return getToolGroup(this, groupId);
    },

    // Toggle tool group expansion
    toggleToolGroup(groupId) {
      const group = this.getToolGroup(groupId);
      if (group) {
        group.expanded = !group.expanded;
      }
    },

    // Delegate to imported tool formatters
    formatToolInput,   // Direct assignment from import
    formatToolOutput,  // Direct assignment from import

    // Reconnect to active session via SSE (no polling!)
    async reconnectToActiveSession() {
      if (!this.sessionId) return;

      console.log('🔄 Reconnecting to active session via SSE');
      this.isStreaming = true;
      this.partialText = '';

      // Find the most recent QueryEvent to get when the current query started
      const lastQueryEvent = [...this.events].reverse().find(e => e.type === 'query' || e.event_type === 'query');

      // Restart real-time metrics tracking when reconnecting to active session
      // Use the actual query start time from the QueryEvent if available
      if (lastQueryEvent && lastQueryEvent.timestamp) {
        // Force UTC parsing by appending 'Z' if timestamp lacks timezone info
        let timestamp = lastQueryEvent.timestamp;
        if (!timestamp.endsWith('Z') && !timestamp.includes('+') && !timestamp.includes('T00:00')) {
          timestamp = timestamp + 'Z';
        }

        const queryStartTime = new Date(timestamp).getTime();
        console.log('🕐 Reconnecting timer from QueryEvent timestamp:', lastQueryEvent.timestamp, '→ (UTC)', timestamp, '→', queryStartTime);

        // Validate the parsed timestamp (should be in the past, not future)
        if (!isNaN(queryStartTime) && queryStartTime > 0 && queryStartTime <= Date.now()) {
          this.startDurationTimerFrom(queryStartTime);
        } else {
          console.warn('⚠️ Invalid QueryEvent timestamp (in future or invalid), using current time');
          this.startDurationTimer();
        }
      } else {
        console.log('🕐 No QueryEvent found, starting timer from now');
        this.startDurationTimer();
      }
      this.isMetricsLive = true;

      try {
        // Reconnect to SSE stream with empty prompt
        // Backend detects active query and subscribes to ongoing events
        const stream = this.api.createEventStream(this.sessionId, '');

        stream
          .on('message', (event) => {
            // Set isLoadingHistory flag when processing historical events during reconnect
            this.isLoadingHistory = true;
            this.handleEvent(event);
            this.isLoadingHistory = false;
          })
          .on('error', (error) => {
            console.error('SSE reconnection error:', error);
            this.isStreaming = false;
            this.stopDurationTimer();
          })
          .on('end', () => {
            console.log('🟢 SSE stream ended');
            this.isStreaming = false;
          });

        await stream.start();
      } catch (error) {
        console.error('Failed to reconnect to SSE stream:', error);
        this.isStreaming = false;
        this.stopDurationTimer();
      }
    },

  };
}
