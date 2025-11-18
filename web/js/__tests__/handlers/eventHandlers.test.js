import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  dispatchEvent,
  handlePartialMessageEvent,
  handleMessageEvent,
  handleToolUseEvent,
  handleCompleteEvent,
} from '../../handlers/eventHandlers.js';

describe('dispatchEvent', () => {
  let mockContext;

  beforeEach(() => {
    mockContext = {
      partialText: '',
      scrollToBottom: vi.fn(),
      addMessage: vi.fn(),
      currentToolGroupId: null,
      toolGroups: [],
      messages: [],
      plans: [],
      approvals: [],
      isStreaming: false,
      focusInput: vi.fn(),
      handleApprovalRequest: vi.fn(),
      handleApprovalResponse: vi.fn(),
      getCurrentPlan: vi.fn(),
      getCurrentToolGroup: vi.fn(),
      // Metrics tracking (added for accumulation support)
      metrics: {
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        totalCost: 0,
        durationMs: 0,
        numTurns: 0,
        messagesCount: 0,
        toolsCount: 0,
      },
      // Accumulated metrics from completed queries
      accumulatedDurationMs: 0,
      accumulatedInputTokens: 0,
      accumulatedOutputTokens: 0,
      // Current query token estimates
      currentQueryInputTokens: 0,
      currentQueryOutputTokens: 0,
    };
  });

  it('should route query events to handleQueryEvent', () => {
    const consoleSpy = vi.spyOn(console, 'log');
    const event = { type: 'query', prompt: 'test query' };

    dispatchEvent(mockContext, event);

    expect(consoleSpy).toHaveBeenCalledWith('Query started:', 'test query');
    consoleSpy.mockRestore();
  });

  it('should route partial_message events to handlePartialMessageEvent', () => {
    mockContext.isStreaming = true; // Partial messages only occur during streaming
    const event = { type: 'partial_message', delta: 'Hello' };

    dispatchEvent(mockContext, event);

    expect(mockContext.partialText).toBe('Hello');
  });

  it('should route message events to handleMessageEvent', () => {
    const event = {
      type: 'message',
      content: 'Response text',
      timestamp: '2024-01-01T00:00:00Z',
      event_id: 'evt123',
    };

    dispatchEvent(mockContext, event);

    expect(mockContext.addMessage).toHaveBeenCalledWith(
      'assistant',
      'Response text',
      undefined,
      '2024-01-01T00:00:00Z',
      'evt123'
    );
  });

  it('should route tool_use events to handleToolUseEvent', () => {
    const event = {
      type: 'tool_use',
      tool_name: 'Bash',
      originated_from_message_id: 'msg1',
    };

    dispatchEvent(mockContext, event);

    expect(mockContext.toolGroups.length).toBe(1);
    expect(mockContext.currentToolGroupId).toBeTruthy();
  });

  it('should route complete events to handleCompleteEvent', () => {
    const event = {
      type: 'complete',
      duration_ms: 1000,
      total_cost_usd: 0.05,
    };

    dispatchEvent(mockContext, event);

    expect(mockContext.isStreaming).toBe(false);
    expect(mockContext.focusInput).toHaveBeenCalled();
  });

  it('should handle event_type field (alternative)', () => {
    const event = { event_type: 'query', prompt: 'test' };
    const consoleSpy = vi.spyOn(console, 'log');

    dispatchEvent(mockContext, event);

    expect(consoleSpy).toHaveBeenCalledWith('Query started:', 'test');
    consoleSpy.mockRestore();
  });

  it('should log unknown event types', () => {
    const consoleSpy = vi.spyOn(console, 'log');
    const event = { type: 'unknown_type', data: 'test' };

    dispatchEvent(mockContext, event);

    expect(consoleSpy).toHaveBeenCalledWith('Unknown event type:', 'unknown_type', event);
    consoleSpy.mockRestore();
  });
});

describe('handlePartialMessageEvent', () => {
  let mockContext;

  beforeEach(() => {
    mockContext = {
      isStreaming: true, // Partial messages only occur during live streaming
      partialText: '',
      scrollToBottom: vi.fn(),
      metrics: {
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        totalCost: 0,
      },
      accumulatedInputTokens: 0,
      accumulatedOutputTokens: 0,
      currentQueryInputTokens: 0,
      currentQueryOutputTokens: 0,
    };
  });

  it('should append delta to partialText', () => {
    handlePartialMessageEvent(mockContext, { delta: 'Hello' });
    expect(mockContext.partialText).toBe('Hello');

    handlePartialMessageEvent(mockContext, { delta: ' World' });
    expect(mockContext.partialText).toBe('Hello World');
  });

  it('should call scrollToBottom', () => {
    handlePartialMessageEvent(mockContext, { delta: 'test' });
    expect(mockContext.scrollToBottom).toHaveBeenCalled();
  });
});

describe('handleMessageEvent', () => {
  let mockContext;

  beforeEach(() => {
    mockContext = {
      partialText: 'some partial text',
      addMessage: vi.fn(),
      metrics: {
        messagesCount: 0,
      },
    };
  });

  it('should clear partialText', () => {
    handleMessageEvent(mockContext, { content: 'final message' });
    expect(mockContext.partialText).toBe('');
  });

  it('should add message with content', () => {
    const event = {
      content: 'Response text',
      timestamp: '2024-01-01T00:00:00Z',
      event_id: 'evt123',
    };

    handleMessageEvent(mockContext, event);

    expect(mockContext.addMessage).toHaveBeenCalledWith(
      'assistant',
      'Response text',
      undefined,
      '2024-01-01T00:00:00Z',
      'evt123'
    );
  });

  it('should add message with thinking', () => {
    const event = {
      thinking: 'Internal thoughts',
      timestamp: '2024-01-01T00:00:00Z',
      event_id: 'evt456',
    };

    handleMessageEvent(mockContext, event);

    expect(mockContext.addMessage).toHaveBeenCalledWith(
      'assistant',
      undefined,
      'Internal thoughts',
      '2024-01-01T00:00:00Z',
      'evt456'
    );
  });

  it('should not add message if no content or thinking', () => {
    handleMessageEvent(mockContext, {});
    expect(mockContext.addMessage).not.toHaveBeenCalled();
  });
});

describe('handleToolUseEvent', () => {
  let mockContext;

  beforeEach(() => {
    mockContext = {
      currentToolGroupId: null,
      toolGroups: [],
      messages: [],
      getCurrentToolGroup: vi.fn(),
      metrics: {
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        totalCost: 0,
        toolsCount: 0,
      },
      accumulatedInputTokens: 0,
      accumulatedOutputTokens: 0,
      currentQueryInputTokens: 0,
      currentQueryOutputTokens: 0,
    };
  });

  it('should create new tool group for first tool', () => {
    const event = {
      tool_name: 'Bash',
      originated_from_message_id: 'msg1',
      timestamp: Date.now(),
    };

    // Mock getCurrentToolGroup to return the created group
    mockContext.getCurrentToolGroup = vi.fn(() => mockContext.toolGroups[0]);

    handleToolUseEvent(mockContext, event);

    expect(mockContext.toolGroups.length).toBe(1);
    expect(mockContext.currentToolGroupId).toBeTruthy();
    expect(mockContext.toolGroups[0].tools.length).toBe(1);
  });

  it('should add tool to existing group for same message', () => {
    const event1 = {
      tool_name: 'Bash',
      originated_from_message_id: 'msg1',
      timestamp: Date.now(),
    };
    const event2 = {
      tool_name: 'Write',
      originated_from_message_id: 'msg1',
      timestamp: Date.now(),
    };

    // Mock to return the group that will be created
    mockContext.getCurrentToolGroup = vi.fn(() => {
      return mockContext.toolGroups[0];
    });

    handleToolUseEvent(mockContext, event1);
    handleToolUseEvent(mockContext, event2);

    expect(mockContext.toolGroups.length).toBe(1);
    expect(mockContext.toolGroups[0].tools.length).toBe(2);
  });

  it('should create new group for different message', () => {
    const event1 = {
      tool_name: 'Bash',
      originated_from_message_id: 'msg1',
    };
    const event2 = {
      tool_name: 'Write',
      originated_from_message_id: 'msg2',
    };

    handleToolUseEvent(mockContext, event1);
    handleToolUseEvent(mockContext, event2);

    expect(mockContext.toolGroups.length).toBe(2);
  });
});

describe('handleCompleteEvent', () => {
  let mockContext;

  beforeEach(() => {
    mockContext = {
      isStreaming: true,
      focusInput: vi.fn(),
      metrics: {
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        totalCost: 0,
        durationMs: 0,
        numTurns: 0,
      },
      accumulatedDurationMs: 0,
      accumulatedInputTokens: 0,
      accumulatedOutputTokens: 0,
    };
  });

  it('should set isStreaming to false', () => {
    handleCompleteEvent(mockContext, {});
    expect(mockContext.isStreaming).toBe(false);
  });

  it('should call focusInput', () => {
    handleCompleteEvent(mockContext, {});
    expect(mockContext.focusInput).toHaveBeenCalled();
  });
});
