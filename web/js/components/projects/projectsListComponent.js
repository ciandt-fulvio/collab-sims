/**
 * Projects List Component
 * Displays projects with their sessions in a hierarchical view
 */

import { SimsAPI } from '../../services/api.js?v=7';
import { initTheme, toggleTheme as toggleThemeUtil } from '../../utils/theme.js?v=7';

export function projectsListComponent() {
  return {
    // API client
    api: new SimsAPI(),

    // State
    projects: [],
    sessions: [],
    agents: [],
    processTypes: [],
    loading: false,
    error: null,
    theme: initTheme(),
    expandedProjects: new Set(),
    creatingSessionFor: null,

    // New project modal state
    showCreateModal: false,
    newProject: {
      name: '',
      title: '',
      processType: '',
      description: ''
    },
    creatingProject: false,

    // Initialize
    async init() {
      await this.loadData();
    },

    // Load all data (projects, sessions, agents, processTypes)
    async loadData() {
      this.loading = true;
      this.error = null;

      try {
        // Load in parallel
        const [projectsResponse, sessionsResponse, agentsResponse, processTypesResponse] = await Promise.all([
          this.api.listProjects(),
          this.api.listSessions(),
          this.api.listAgents(),
          this.api.listProcessTypes()
        ]);

        this.projects = projectsResponse.projects || [];
        this.sessions = sessionsResponse.sessions || [];
        this.agents = agentsResponse.agents || [];
        this.processTypes = processTypesResponse.process_types || [];

        // Sort projects by updated_at or created_at (newest first)
        this.projects.sort((a, b) => {
          const dateA = new Date(a.updated_at || a.created_at || 0);
          const dateB = new Date(b.updated_at || b.created_at || 0);
          return dateB - dateA;
        });

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

    // Open create project modal
    openCreateModal() {
      this.newProject = {
        name: '',
        title: '',
        processType: this.processTypes.length > 0 ? this.processTypes[0].id : '',
        description: ''
      };
      this.showCreateModal = true;
    },

    // Close create project modal
    closeCreateModal() {
      this.showCreateModal = false;
    },

    // Generate project name from title (slug)
    generateProjectName() {
      if (this.newProject.title) {
        this.newProject.name = this.newProject.title
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-|-$/g, '');
      }
    },

    // Create new project
    async createProject() {
      if (!this.newProject.name || !this.newProject.title || !this.newProject.processType) {
        alert('Please fill in all required fields');
        return;
      }

      this.creatingProject = true;

      try {
        const now = new Date().toISOString().split('T')[0];
        const content = `---
name: ${this.newProject.name}
title: ${this.newProject.title}
type: ${this.newProject.processType}
created_at: ${now}
updated_at: ${now}
status: active
---

# ${this.newProject.title}

${this.newProject.description || 'Project description goes here.'}
`;

        await this.api.createProject(this.newProject.name, content);
        this.closeCreateModal();
        await this.loadData();
      } catch (err) {
        console.error('Failed to create project:', err);
        alert('Failed to create project: ' + err.message);
      } finally {
        this.creatingProject = false;
      }
    },

    // Get sessions for a specific project (sorted by creation date, newest first)
    getProjectSessions(projectName) {
      return this.sessions
        .filter(s => s.project_name === projectName)
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
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
