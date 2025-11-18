/**
 * Sessions List Component
 * Handles listing, viewing, and deleting sessions
 */

import { SimsAPI } from '../../services/api.js?v=4';
import { initTheme, toggleTheme as toggleThemeUtil } from '../../utils/theme.js?v=4';

export function sessionsListComponent() {
  return {
    // API client
    api: new SimsAPI(),

    // State
    sessions: [],
    loading: false,
    error: null,
    theme: initTheme(),
    showSessionTypeMenu: false,
    creatingSession: false,

    // Initialize
    async init() {
      const params = new URLSearchParams(window.location.search);

      // If session ID is present, redirect to chat interface
      const sessionId = params.get('id');
      if (sessionId) {
        window.location.href = `/sessions/chat.html?id=${sessionId}`;
        return;
      }

      // Load sessions list
      await this.loadSessions();
    },

    // Load all sessions
    async loadSessions() {
      this.loading = true;
      this.error = null;

      try {
        const response = await this.api.listSessions();
        this.sessions = response.sessions || [];
      } catch (err) {
        console.error('Failed to load sessions:', err);
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    // Navigate to session
    viewSession(sessionId) {
      window.location.href = `/sessions/chat.html?id=${sessionId}`;
    },

    // Delete a session
    async deleteSession(sessionId) {
      if (!confirm('Are you sure you want to delete this session? This cannot be undone.')) {
        return;
      }

      try {
        await this.api.deleteSession(sessionId);
        await this.loadSessions();
      } catch (err) {
        console.error('Failed to delete session:', err);
        alert('Failed to delete session: ' + err.message);
      }
    },

    // Toggle theme
    toggleTheme() {
      this.theme = toggleThemeUtil();
    },

    // Format date for display
    formatDate(dateString) {
      if (!dateString) return 'N/A';
      const date = new Date(dateString);
      return date.toLocaleString();
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
        // Visual feedback: could add a toast notification here
        console.log('Copied to clipboard:', text);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    },

    // Create new session with specified type
    async createNewSession(sessionType) {
      this.creatingSession = true;
      this.showSessionTypeMenu = false;

      try {
        const response = await this.api.createSession({
          include_partial_messages: true,
          approval_config: {
            mode: 'auto',
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
        }, sessionType);

        // Redirect to the new session
        window.location.href = `/sessions/chat.html?id=${response.session_id}`;
      } catch (err) {
        console.error('Failed to create session:', err);
        alert('Failed to create session: ' + err.message);
        this.creatingSession = false;
      }
    }
  };
}
