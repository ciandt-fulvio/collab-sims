/**
 * Projects List Component
 * Displays projects with their sessions in a hierarchical view
 */

import { SimsAPI } from '../../services/api.js?v=5';
import { initTheme, toggleTheme as toggleThemeUtil } from '../../utils/theme.js?v=5';

export function projectsListComponent() {
  return {
    // API client
    api: new SimsAPI(),

    // State
    projects: [],
    sessions: [],
    agents: [],
    loading: false,
    error: null,
    theme: initTheme(),
    expandedProjects: new Set(),
    creatingSessionFor: null,

    // Initialize
    async init() {
      await this.loadData();
    },

    // Load all data (projects, sessions, agents)
    async loadData() {
      this.loading = true;
      this.error = null;

      try {
        // Load in parallel
        const [projectsResponse, sessionsResponse, agentsResponse] = await Promise.all([
          this.api.listProjects(),
          this.api.listSessions(),
          this.api.listAgents()
        ]);

        this.projects = projectsResponse.projects || [];
        this.sessions = sessionsResponse.sessions || [];
        this.agents = agentsResponse.agents || [];

        // Auto-expand projects that have sessions
        this.projects.forEach(project => {
          const hasSessions = this.getProjectSessions(project.name).length > 0;
          if (hasSessions) {
            this.expandedProjects.add(project.name);
          }
        });
      } catch (err) {
        console.error('Failed to load data:', err);
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    // Get sessions for a specific project
    getProjectSessions(projectName) {
      return this.sessions.filter(s => s.project_name === projectName);
    },

    // Toggle project expansion
    toggleProject(projectName) {
      if (this.expandedProjects.has(projectName)) {
        this.expandedProjects.delete(projectName);
      } else {
        this.expandedProjects.add(projectName);
      }
      // Force Alpine reactivity
      this.expandedProjects = new Set(this.expandedProjects);
    },

    // Check if project is expanded
    isProjectExpanded(projectName) {
      return this.expandedProjects.has(projectName);
    },

    // Create new session (agents are selected dynamically by LLM)
    async createSession(projectName) {
      this.creatingSessionFor = projectName;

      try {
        const response = await this.api.createSession(projectName, null, {
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
        });

        // Redirect to the new session
        window.location.href = `/projects/chat.html?id=${response.session_id}`;
      } catch (err) {
        console.error('Failed to create session:', err);
        alert('Failed to create session: ' + err.message);
        this.creatingSessionFor = null;
      }
    },

    // Navigate to session
    viewSession(sessionId) {
      window.location.href = `/projects/chat.html?id=${sessionId}`;
    },

    // Delete a session
    async deleteSession(sessionId, event) {
      event.stopPropagation();

      if (!confirm('Are you sure you want to delete this session? This cannot be undone.')) {
        return;
      }

      try {
        await this.api.deleteSession(sessionId);
        await this.loadData();
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

    // Get agent display name
    getAgentDisplayName(agentName) {
      if (!agentName) return 'No agent';
      const agent = this.agents.find(a => a.name === agentName);
      return agent ? agent.description || agentName : agentName;
    },

    // Copy to clipboard
    async copyToClipboard(text, event) {
      event.stopPropagation();
      try {
        await navigator.clipboard.writeText(text);
        console.log('Copied to clipboard:', text);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    }
  };
}
