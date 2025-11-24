/**
 * Markdown Viewer/Editor Component
 * Displays and edits markdown files with frontmatter support
 */

import { SimsAPI } from '../../services/api.js?v=5';

export function mdViewerComponent(resourceType, resourceName) {
  return {
    // API client
    api: new SimsAPI(),

    // Resource info
    resourceType: resourceType, // 'project', 'agent', or 'activity_script'
    resourceName: resourceName,

    // State
    loading: false,
    error: null,
    editing: false,
    saving: false,

    // Content
    frontmatter: {},
    content: '',
    rawContent: '',

    // Edited content (when in edit mode)
    editedRawContent: '',

    // Initialize
    async init() {
      await this.loadContent();
    },

    // Load markdown content
    async loadContent() {
      this.loading = true;
      this.error = null;

      try {
        let response;

        switch (this.resourceType) {
          case 'project':
            response = await this.api.getProject(this.resourceName);
            break;
          case 'agent':
            response = await this.api.getAgent(this.resourceName);
            break;
          case 'activity_script':
            response = await this.api.getActivityScript(this.resourceName);
            break;
          default:
            throw new Error(`Unknown resource type: ${this.resourceType}`);
        }

        this.frontmatter = response.frontmatter || {};
        this.content = response.content || '';
        this.rawContent = response.raw_content || '';
        this.editedRawContent = this.rawContent;
      } catch (err) {
        console.error('Failed to load content:', err);
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    // Start editing
    startEditing() {
      this.editing = true;
      this.editedRawContent = this.rawContent;
    },

    // Cancel editing
    cancelEditing() {
      this.editing = false;
      this.editedRawContent = this.rawContent;
      this.error = null;
    },

    // Save changes
    async saveChanges() {
      this.saving = true;
      this.error = null;

      try {
        switch (this.resourceType) {
          case 'project':
            await this.api.updateProject(this.resourceName, this.editedRawContent);
            break;
          case 'agent':
            await this.api.updateAgent(this.resourceName, this.editedRawContent);
            break;
          case 'activity_script':
            await this.api.updateActivityScript(this.resourceName, this.editedRawContent);
            break;
        }

        // Reload to get parsed content
        await this.loadContent();
        this.editing = false;
      } catch (err) {
        console.error('Failed to save changes:', err);
        this.error = 'Failed to save: ' + err.message;
      } finally {
        this.saving = false;
      }
    },

    // Get display title
    getTitle() {
      return this.frontmatter.title || this.frontmatter.name || this.resourceName;
    },

    // Get description
    getDescription() {
      return this.frontmatter.description || '';
    },

    // Render markdown to HTML (simple implementation)
    renderMarkdown(markdown) {
      if (typeof marked !== 'undefined') {
        return marked.parse(markdown);
      }
      // Fallback: simple line break conversion
      return markdown.replace(/\n/g, '<br>');
    },

    // Get frontmatter as formatted YAML
    getFrontmatterDisplay() {
      const lines = ['---'];
      for (const [key, value] of Object.entries(this.frontmatter)) {
        if (Array.isArray(value)) {
          lines.push(`${key}:`);
          value.forEach(item => lines.push(`  - ${item}`));
        } else if (typeof value === 'object') {
          lines.push(`${key}:`);
          for (const [subKey, subValue] of Object.entries(value)) {
            lines.push(`  ${subKey}: ${subValue}`);
          }
        } else {
          lines.push(`${key}: ${value}`);
        }
      }
      lines.push('---');
      return lines.join('\n');
    },

    // Get resource type label
    getResourceTypeLabel() {
      switch (this.resourceType) {
        case 'project':
          return 'Project';
        case 'agent':
          return 'Agent';
        case 'activity_script':
          return 'Activity Script';
        default:
          return 'Resource';
      }
    }
  };
}
