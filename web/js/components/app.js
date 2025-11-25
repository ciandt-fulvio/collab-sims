/**
 * Main Alpine.js component
 * Refactored to use modular imports for maintainability
 */

import { SimsAPI } from '../services/api.js?v=8';
import { formatToolInput, formatToolOutput } from '../utils/toolFormatters.js?v=8';
import { escapeHtml, renderMarkdown, getEventSummary } from '../utils/rendering.js?v=8';
import { dispatchEvent } from '../handlers/eventHandlers.js?v=8';
import {
  getCurrentToolGroup,
  getToolGroup
} from '../state/sessionState.js?v=8';
import { initTheme, toggleTheme as toggleThemeUtil } from '../utils/theme.js?v=8';
import { metricsPanel } from './chat/metricsPanel.js?v=8';
import { planPanel } from './chat/planPanel.js?v=8';
import { eventsPanel } from './chat/eventsPanel.js?v=8';
import { approvalsPanel } from './chat/approvalsPanel.js?v=8';

export function simsApp() {
  return {
    // API client
    api: new SimsAPI(),

    // Session state
    sessionId: null,
    projectName: null,  // project name (ID) for this session
    projectTitle: null,  // project title (display name) from project metadata
    projectType: null,  // project type (loaded from project metadata)
    agentName: null,    // agent name if specified
    sessionName: null,  // session name (from first message)
    sessionNameCaptured: false,  // flag to capture only once
    isStreaming: false,
    isInitializing: true,
    _initCalled: false,  // Guard flag to prevent double initialization
    isLoadingHistory: false,  // Flag to distinguish history load from live streaming
    isRestoringSession: false,  // Flag for showing skeleton UI during session load

    // Theme state (light, dark, or system) - managed by theme utility
    theme: initTheme(),


    // UI state
    activeTab: 'project',
    prompt: '',
    partialText: '',

    // Data
    messages: [],

    // Library resources (for MD viewer tabs)
    projects: [],
    agents: [],
    selectedResource: null,  // For viewing/editing in MD viewer

    // Process progress state (Project tab)
    processProgress: null,
    loadingProcessProgress: false,
    expandedStages: new Set(),

    // Activity results state (Activities tab)
    activityResults: null,
    loadingActivityResults: false,
    expandedActivityGroups: new Set(),

    // Document editor modal state
    showDocumentModal: false,
    activeDocument: null,  // { docType, docName, projectName, content, frontmatter, versions, isEditing, originalContent }

    // Component composition
    ...metricsPanel(),
    ...planPanel(),
    ...eventsPanel(),
    ...approvalsPanel(),

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

    // Create new session - redirect to projects list
    async createSession() {
      console.log('🟡 createSession() called - redirecting to projects list');
      // Sessions must be created from the projects list page now
      window.location.href = '/projects/';
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
        this.sessionNameCaptured = false;  // Reset for new session

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
        this.projectName = session.project_name || null;
        this.agentName = session.agent_name || null;
        this.sessionName = session.session_name || null;  // Load existing session name

        // Load project metadata if project name exists
        if (this.projectName) {
          try {
            const projectData = await this.api.getProject(this.projectName);
            this.projectTitle = projectData.frontmatter?.title || null;
            this.projectType = projectData.frontmatter?.type || null;
          } catch (e) {
            console.warn('Failed to load project metadata:', e);
            this.projectTitle = null;
            this.projectType = null;
          }
        }

        // If session already has a name, mark as captured to prevent overwrite
        if (this.sessionName) {
          this.sessionNameCaptured = true;
        }
        console.log('🟢 Session loaded:', session);

        // Load library resources for MD viewer tabs
        await this.loadLibraryResources();

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

        // ✅ Use execution_state from API to determine if session is actually executing
        // This is more reliable than inferring from events, especially for resumed sessions
        const isExecuting = session.execution_state === 'executing';

        if (isExecuting) {
          console.log('🔵 Session is executing, reconnecting to SSE...');
          // ⚠️ Set streaming state BEFORE reconnecting so UI shows loading immediately
          this.isStreaming = true;
          // Reconnect to ongoing SSE stream
          this.reconnectToActiveSession();
        } else {
          console.log('🟢 Session is idle and ready for new queries');
          // ✅ Ensure streaming is disabled for idle sessions
          this.isStreaming = false;
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

    // Load library resources for MD viewer tabs
    async loadLibraryResources() {
      try {
        const [projectsRes, agentsRes] = await Promise.all([
          this.api.listProjects(),
          this.api.listAgents(),
        ]);
        this.projects = projectsRes.projects || [];
        this.agents = agentsRes.agents || [];
      } catch (err) {
        console.error('Failed to load library resources:', err);
      }
    },

    // Load process progress for Project tab
    async loadProcessProgress() {
      if (!this.projectName) {
        console.warn('No project name available');
        return;
      }

      this.loadingProcessProgress = true;
      try {
        const response = await this.api.getProjectProcessProgress(this.projectName);
        this.processProgress = response;
      } catch (err) {
        console.error('Failed to load process progress:', err);
        this.processProgress = null;
      } finally {
        this.loadingProcessProgress = false;
      }
    },

    // Load activity results for Activities tab
    async loadActivityResults() {
      if (!this.projectName) {
        console.warn('No project name available');
        return;
      }

      this.loadingActivityResults = true;
      try {
        const response = await this.api.getProjectActivityResults(this.projectName);
        this.activityResults = response;
      } catch (err) {
        console.error('Failed to load activity results:', err);
        this.activityResults = null;
      } finally {
        this.loadingActivityResults = false;
      }
    },

    // Stage expansion toggle
    toggleStageExpansion(stageId) {
      if (this.expandedStages.has(stageId)) {
        this.expandedStages.delete(stageId);
      } else {
        this.expandedStages.add(stageId);
      }
      // Force reactivity
      this.expandedStages = new Set(this.expandedStages);
    },

    isStageExpanded(stageId) {
      return this.expandedStages.has(stageId);
    },

    toggleActivityGroupExpansion(groupScript) {
      if (this.expandedActivityGroups.has(groupScript)) {
        this.expandedActivityGroups.delete(groupScript);
      } else {
        this.expandedActivityGroups.add(groupScript);
      }
      // Force reactivity
      this.expandedActivityGroups = new Set(this.expandedActivityGroups);
    },

    isActivityGroupExpanded(groupScript) {
      return this.expandedActivityGroups.has(groupScript);
    },

    // Progress calculation helpers
    calculateTotalActivities(processProgress) {
      if (!processProgress?.stages) return 0;
      return processProgress.stages.reduce((total, stage) => {
        return total + (stage.activities?.length || 0);
      }, 0);
    },

    calculateTotalCompleted(processProgress) {
      if (!processProgress?.stages) return 0;
      return processProgress.stages.reduce((total, stage) => {
        return total + (stage.completion_count || 0);
      }, 0);
    },

    calculateProgressPercentage(processProgress) {
      const total = this.calculateTotalActivities(processProgress);
      if (total === 0) return 0;
      const completed = this.calculateTotalCompleted(processProgress);
      return Math.round((completed / total) * 100);
    },

    // View activity result (placeholder for future modal)
    viewActivityResult(execution) {
      console.log('View result:', execution.path);
      alert(`View result: ${execution.filename}\n\nPath: ${execution.path}\n\nThis will open in a modal viewer (future enhancement)`);
    },

    // View activity outputs - navigates to Activities tab and expands the activity
    viewActivityOutputs(activity) {
      console.log('View activity outputs:', activity.title);

      // Add a system message with a link to outputs
      const message = `📋 ${activity.title}`;
      this.addMessage('system', message);

      // Store the activity script to expand in Activities tab
      this._targetActivityScript = activity.script;

      // Load activity results if not already loaded
      if (!this.activityResults) {
        this.loadActivityResults().then(() => {
          this._navigateToActivityInTab();
        });
      } else {
        this._navigateToActivityInTab();
      }

      // Switch to Activities tab
      this.activeTab = 'activities';
    },

    // Helper to navigate to specific activity in Activities tab
    _navigateToActivityInTab() {
      if (!this._targetActivityScript) return;

      const targetScript = this._targetActivityScript;
      this._targetActivityScript = null;

      // Collapse all activity groups
      this.expandedActivityGroups.clear();

      // Expand the target activity group
      this.expandedActivityGroups.add(targetScript);

      // Force reactivity
      this.expandedActivityGroups = new Set(this.expandedActivityGroups);

      // Scroll to the Activities tab content
      this.$nextTick(() => {
        const activitiesTab = document.querySelector('[x-show="activeTab === \'activities\'"]');
        if (activitiesTab) {
          activitiesTab.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    },

    // View agent details using document modal
    viewAgentDetails(agent) {
      console.log('View agent details:', agent.name);
      this.openDocument('agent', agent.name);
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
      // ✅ Don't set isStreaming = true here! Let events control streaming state.
      // This prevents input from being blocked when reconnecting to idle sessions.
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

    // ===== Document Editor Modal Methods =====

    // Open a document in the modal for viewing/editing
    async openDocument(docType, docName, projectName = null) {
      try {
        console.log('📄 Opening document in modal:', { docType, docName, projectName });

        // Check if same document is already open
        if (this.activeDocument &&
            this.activeDocument.docType === docType &&
            this.activeDocument.docName === docName &&
            this.activeDocument.projectName === projectName) {
          console.log('Document already open in modal');
          this.showDocumentModal = true;
          return;
        }

        // Check for unsaved changes in currently open document
        if (this.activeDocument &&
            this.activeDocument.isEditing &&
            this.activeDocument.content !== this.activeDocument.originalContent) {
          if (!confirm('You have unsaved changes in the current document. Discard and open new document?')) {
            return;
          }
        }

        // Load document from API
        const docData = await this.api.loadDocument(docType, docName, projectName);

        // Set as active document
        this.activeDocument = {
          docType,
          docName,
          projectName,
          content: docData.content,  // Content without frontmatter (for display)
          rawContent: docData.raw_content,  // Full content with frontmatter (for editing)
          frontmatter: docData.frontmatter,
          versions: docData.versions || [],
          isEditing: false,
          originalRawContent: docData.raw_content,
        };

        // Show the modal
        this.showDocumentModal = true;

        console.log('✅ Document opened in modal successfully');
      } catch (error) {
        console.error('Failed to open document:', error);
        alert(`Failed to open document: ${error.message}`);
      }
    },

    // Close the document modal
    closeDocumentModal() {
      if (!this.activeDocument) {
        this.showDocumentModal = false;
        return;
      }

      // Check if there are unsaved changes
      if (this.activeDocument.isEditing &&
          this.activeDocument.rawContent !== this.activeDocument.originalRawContent) {
        if (!confirm('You have unsaved changes. Are you sure you want to close this document?')) {
          return;
        }
      }

      this.showDocumentModal = false;
      this.activeDocument = null;
      console.log('📄 Document modal closed');
    },

    // Toggle between view and edit mode in modal
    toggleDocumentEdit() {
      if (!this.activeDocument) return;

      this.activeDocument.isEditing = !this.activeDocument.isEditing;

      // If switching to edit mode, focus the textarea
      if (this.activeDocument.isEditing) {
        this.$nextTick(() => {
          const textarea = document.querySelector('#document-modal-textarea');
          if (textarea) {
            textarea.focus();
          }
        });
      }
    },

    // Save document (overwrite)
    async saveDocumentContent() {
      if (!this.activeDocument) return;

      const doc = this.activeDocument;

      try {
        console.log('💾 Saving document:', doc.docName);
        await this.api.saveDocument(doc.docType, doc.docName, doc.rawContent, doc.projectName);

        // Update original content to match saved content
        doc.originalRawContent = doc.rawContent;

        // Switch back to view mode
        doc.isEditing = false;

        console.log('✅ Document saved successfully');

        // Show success message
        this.addMessage('system', `📄 Document "${doc.docName}" saved successfully`);
      } catch (error) {
        console.error('Failed to save document:', error);
        alert(`Failed to save document: ${error.message}`);
      }
    },

    // Save document as new version
    async saveDocumentAsVersion() {
      if (!this.activeDocument) return;

      const doc = this.activeDocument;

      try {
        console.log('💾 Saving document as new version:', doc.docName);
        const response = await this.api.saveDocumentVersion(doc.docType, doc.docName, doc.rawContent, doc.projectName);

        // Update versions list
        if (response.filename) {
          doc.versions.push(response.filename);
        }

        // Update original content to match saved content
        doc.originalRawContent = doc.rawContent;

        // Switch back to view mode
        doc.isEditing = false;

        console.log('✅ New version created:', response.filename);

        // Show success message
        this.addMessage('system', `📄 New version created: ${response.filename}`);
      } catch (error) {
        console.error('Failed to save document version:', error);
        alert(`Failed to save document version: ${error.message}`);
      }
    },

  };
}
