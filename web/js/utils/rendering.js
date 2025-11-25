/**
 * Rendering utilities for markdown, HTML escaping, and event summaries
 */

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Render markdown to HTML using marked.js
 * Applies syntax highlighting with highlight.js
 * Treats YAML frontmatter specially with compact monospaced styling
 */
export function renderMarkdown(text) {
  if (!text) return '';

  // Check if text starts with YAML frontmatter (--- ... ---)
  let frontmatterHtml = '';
  let markdownContent = text;

  const frontmatterRegex = /^---\n([\s\S]*?)\n---\n([\s\S]*)$/;
  const match = text.match(frontmatterRegex);

  if (match) {
    const frontmatterYaml = match[1];
    markdownContent = match[2];

    // Render frontmatter as compact monospaced block
    const escapedYaml = escapeHtml(frontmatterYaml);
    frontmatterHtml = `<div class="frontmatter-block">${escapedYaml.replace(/\n/g, '<br>')}</div>`;
  }

  // Configure marked options
  marked.setOptions({
    breaks: true,  // Support line breaks
    gfm: true,     // GitHub Flavored Markdown
    highlight: function(code, lang) {
      // Use highlight.js for syntax highlighting
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang }).value;
        } catch (e) {
          console.error('Highlight error:', e);
          return hljs.highlightAuto(code).value;
        }
      }
      // Auto-detect language if not specified
      try {
        return hljs.highlightAuto(code).value;
      } catch (e) {
        console.error('Auto-highlight error:', e);
        return code; // Return plain code if highlighting fails
      }
    }
  });

  const contentHtml = marked.parse(markdownContent);
  return frontmatterHtml + contentHtml;
}

/**
 * Get compact event summary for display in Events tab
 */
export function getEventSummary(event) {
  const eventType = event.type || event.event_type;

  switch (eventType) {
    case 'query':
      return `"${event.prompt?.substring(0, 60)}${event.prompt?.length > 60 ? '...' : ''}"`;
    case 'message':
      return `"${event.content?.substring(0, 60)}${event.content?.length > 60 ? '...' : ''}"`;
    case 'partial_message':
      return `"${event.delta?.substring(0, 40)}${event.delta?.length > 40 ? '...' : ''}"`;
    case 'tool_use':
      return `${event.tool_name}`;
    case 'tool_result':
      return `${event.tool_name || 'Unknown'}`;
    case 'plan':
      return `${event.total_tasks} tasks`;
    case 'progress':
      return `${event.completed}/${event.total} completed`;
    case 'complete':
      return `${event.duration_ms}ms, $${event.total_cost_usd?.toFixed(4)}`;
    case 'error':
      return `${event.error}`;
    case 'approval_request':
      return `${event.tool_name} (${event.risk_level})`;
    case 'approval_response':
      return `${event.approved ? 'Approved' : 'Rejected'}`;
    default:
      return 'Event details';
  }
}
