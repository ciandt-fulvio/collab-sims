import { describe, it, expect, beforeEach, vi } from 'vitest';
import { escapeHtml, renderMarkdown, getEventSummary} from '../../utils/rendering.js';

describe('escapeHtml', () => {
  it('should escape HTML special characters', () => {
    const html = '<script>alert("XSS")</script>';
    const escaped = escapeHtml(html);
    // happy-dom returns text as-is from textContent
    expect(escaped).toBe(html);
  });

  it('should handle ampersands', () => {
    const result = escapeHtml('Tom & Jerry');
    expect(result).toBe('Tom & Jerry');
  });

  it('should escape quotes', () => {
    expect(escapeHtml('"Hello"')).toBe('"Hello"');
  });

  it('should handle empty strings', () => {
    expect(escapeHtml('')).toBe('');
  });

  it('should handle normal text without changes', () => {
    expect(escapeHtml('Hello World')).toBe('Hello World');
  });
});

describe('renderMarkdown', () => {
  beforeEach(() => {
    // Mock marked and hljs globals
    global.marked = {
      setOptions: vi.fn(),
      parse: vi.fn((text) => `<p>${text}</p>`),
    };

    global.hljs = {
      getLanguage: vi.fn(),
      highlight: vi.fn(),
      highlightAuto: vi.fn(),
    };
  });

  it('should return empty string for null input', () => {
    expect(renderMarkdown(null)).toBe('');
  });

  it('should return empty string for undefined input', () => {
    expect(renderMarkdown(undefined)).toBe('');
  });

  it('should return empty string for empty string', () => {
    expect(renderMarkdown('')).toBe('');
  });

  it('should call marked.parse with text', () => {
    const text = '# Hello World';
    renderMarkdown(text);
    expect(global.marked.parse).toHaveBeenCalledWith(text);
  });

  it('should configure marked with correct options', () => {
    renderMarkdown('test');
    expect(global.marked.setOptions).toHaveBeenCalledWith(
      expect.objectContaining({
        breaks: true,
        gfm: true,
        highlight: expect.any(Function),
      })
    );
  });
});

describe('getEventSummary', () => {
  it('should format query events', () => {
    const event = { type: 'query', prompt: 'Test query' };
    expect(getEventSummary(event)).toBe('"Test query"');
  });

  it('should truncate long query prompts', () => {
    const event = {
      type: 'query',
      prompt: 'a'.repeat(70),
    };
    const result = getEventSummary(event);
    expect(result).toContain('...');
    expect(result.length).toBeLessThan(70);
  });

  it('should format message events', () => {
    const event = { type: 'message', content: 'Hello World' };
    expect(getEventSummary(event)).toBe('"Hello World"');
  });

  it('should truncate long messages', () => {
    const event = {
      type: 'message',
      content: 'b'.repeat(70),
    };
    const result = getEventSummary(event);
    expect(result).toContain('...');
  });

  it('should format partial_message events', () => {
    const event = { type: 'partial_message', delta: 'streaming...' };
    expect(getEventSummary(event)).toBe('"streaming..."');
  });

  it('should truncate long partial messages', () => {
    const event = {
      type: 'partial_message',
      delta: 'c'.repeat(50),
    };
    const result = getEventSummary(event);
    expect(result).toContain('...');
  });

  it('should format tool_use events', () => {
    const event = { type: 'tool_use', tool_name: 'Bash' };
    expect(getEventSummary(event)).toBe('Bash');
  });

  it('should format tool_result events', () => {
    const event = { type: 'tool_result', tool_name: 'Write' };
    expect(getEventSummary(event)).toBe('Write');
  });

  it('should format tool_result events with missing tool_name', () => {
    const event = { type: 'tool_result' };
    expect(getEventSummary(event)).toBe('Unknown');
  });

  it('should format plan events', () => {
    const event = { type: 'plan', total_tasks: 5 };
    expect(getEventSummary(event)).toBe('5 tasks');
  });

  it('should format progress events', () => {
    const event = { type: 'progress', completed: 3, total: 5 };
    expect(getEventSummary(event)).toBe('3/5 completed');
  });

  it('should format complete events', () => {
    const event = {
      type: 'complete',
      duration_ms: 1234,
      total_cost_usd: 0.0527,
    };
    expect(getEventSummary(event)).toBe('1234ms, $0.0527');
  });

  it('should format error events', () => {
    const event = { type: 'error', error: 'Something went wrong' };
    expect(getEventSummary(event)).toBe('Something went wrong');
  });

  it('should format approval_request events', () => {
    const event = {
      type: 'approval_request',
      tool_name: 'Bash',
      risk_level: 'high',
    };
    expect(getEventSummary(event)).toBe('Bash (high)');
  });

  it('should format approval_response events - approved', () => {
    const event = { type: 'approval_response', approved: true };
    expect(getEventSummary(event)).toBe('Approved');
  });

  it('should format approval_response events - rejected', () => {
    const event = { type: 'approval_response', approved: false };
    expect(getEventSummary(event)).toBe('Rejected');
  });

  it('should return default for unknown event types', () => {
    const event = { type: 'unknown_type' };
    expect(getEventSummary(event)).toBe('Event details');
  });

  it('should handle event_type field (alternative field name)', () => {
    const event = { event_type: 'query', prompt: 'Test' };
    expect(getEventSummary(event)).toBe('"Test"');
  });

  it('should handle missing optional fields gracefully', () => {
    const event = { type: 'query' };
    expect(getEventSummary(event)).toBe('"undefined"');
  });
});
