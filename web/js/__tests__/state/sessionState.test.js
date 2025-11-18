import { describe, it, expect, beforeEach } from 'vitest';
import {
  createSessionState,
  resetSessionState,
  getCurrentPlan,
  getPreviousPlans,
  getCurrentToolGroup,
  getToolGroup,
  getFilteredEvents,
} from '../../state/sessionState.js';

describe('createSessionState', () => {
  it('should create initial session state with correct structure', () => {
    const state = createSessionState();

    expect(state).toHaveProperty('sessionId', null);
    expect(state).toHaveProperty('messages', []);
    expect(state).toHaveProperty('events', []);
    expect(state).toHaveProperty('plans', []);
    expect(state).toHaveProperty('approvals', []);
    expect(state).toHaveProperty('toolGroups', []);
    expect(state).toHaveProperty('currentToolGroupId', null);
  });

  it('should create streaming state', () => {
    const state = createSessionState();

    expect(state.isStreaming).toBe(false);
    expect(state.partialText).toBe('');
    expect(state.seenMessages).toBeInstanceOf(Set);
    expect(state.seenMessages.size).toBe(0);
  });

  it('should create event filters with correct defaults', () => {
    const state = createSessionState();

    expect(state.eventTypeFilters.query).toBe(true);
    expect(state.eventTypeFilters.message).toBe(true);
    expect(state.eventTypeFilters.partial_message).toBe(false); // Only one disabled by default
    expect(state.eventTypeFilters.tool_use).toBe(true);
    expect(state.eventTypeFilters.complete).toBe(true);
  });
});

describe('resetSessionState', () => {
  let state;

  beforeEach(() => {
    state = createSessionState();
    // Populate state with data
    state.messages = [{ id: 1, content: 'test' }];
    state.events = [{ type: 'query' }];
    state.plans = [{ todos: [] }];
    state.approvals = [{ id: 'a1' }];
    state.toolGroups = [{ id: 'tg1' }];
    state.currentToolGroupId = 'tg1';
    state.partialText = 'partial...';
    state.seenMessages.add('msg1');
    state.expandedEvents.add(1);
    state.expandedPlans.add(0);
  });

  it('should clear all data arrays', () => {
    resetSessionState(state);

    expect(state.messages).toEqual([]);
    expect(state.events).toEqual([]);
    expect(state.plans).toEqual([]);
    expect(state.approvals).toEqual([]);
    expect(state.toolGroups).toEqual([]);
  });

  it('should reset currentToolGroupId', () => {
    resetSessionState(state);
    expect(state.currentToolGroupId).toBeNull();
  });

  it('should clear partialText', () => {
    resetSessionState(state);
    expect(state.partialText).toBe('');
  });

  it('should clear all Sets', () => {
    resetSessionState(state);
    expect(state.seenMessages.size).toBe(0);
    expect(state.expandedEvents.size).toBe(0);
    expect(state.expandedPlans.size).toBe(0);
  });
});

describe('getCurrentPlan', () => {
  let state;

  beforeEach(() => {
    state = createSessionState();
  });

  it('should return null when no plans exist', () => {
    expect(getCurrentPlan(state)).toBeNull();
  });

  it('should return the most recent plan', () => {
    const plan1 = { id: 1, todos: [] };
    const plan2 = { id: 2, todos: [] };
    const plan3 = { id: 3, todos: [] };

    state.plans = [plan1, plan2, plan3];
    expect(getCurrentPlan(state)).toBe(plan3);
  });

  it('should return the only plan if only one exists', () => {
    const plan = { id: 1, todos: [] };
    state.plans = [plan];
    expect(getCurrentPlan(state)).toBe(plan);
  });
});

describe('getPreviousPlans', () => {
  let state;

  beforeEach(() => {
    state = createSessionState();
  });

  it('should return empty array when no plans exist', () => {
    expect(getPreviousPlans(state)).toEqual([]);
  });

  it('should return empty array when only one plan exists', () => {
    state.plans = [{ id: 1 }];
    expect(getPreviousPlans(state)).toEqual([]);
  });

  it('should return all except most recent plan in reverse order', () => {
    const plan1 = { id: 1 };
    const plan2 = { id: 2 };
    const plan3 = { id: 3 };

    state.plans = [plan1, plan2, plan3];
    const previous = getPreviousPlans(state);

    expect(previous).toHaveLength(2);
    expect(previous[0]).toBe(plan2); // Reversed
    expect(previous[1]).toBe(plan1); // Reversed
  });
});

describe('getCurrentToolGroup', () => {
  let state;

  beforeEach(() => {
    state = createSessionState();
  });

  it('should return null when currentToolGroupId is null', () => {
    expect(getCurrentToolGroup(state)).toBeNull();
  });

  it('should return the current tool group', () => {
    const group1 = { id: 'tg1', tools: [] };
    const group2 = { id: 'tg2', tools: [] };

    state.toolGroups = [group1, group2];
    state.currentToolGroupId = 'tg2';

    expect(getCurrentToolGroup(state)).toBe(group2);
  });

  it('should return null if current group ID not found', () => {
    const group = { id: 'tg1', tools: [] };
    state.toolGroups = [group];
    state.currentToolGroupId = 'tg999';

    expect(getCurrentToolGroup(state)).toBeUndefined();
  });
});

describe('getToolGroup', () => {
  let state;

  beforeEach(() => {
    state = createSessionState();
  });

  it('should return tool group by ID', () => {
    const group1 = { id: 'tg1', tools: [] };
    const group2 = { id: 'tg2', tools: [] };

    state.toolGroups = [group1, group2];
    expect(getToolGroup(state, 'tg1')).toBe(group1);
    expect(getToolGroup(state, 'tg2')).toBe(group2);
  });

  it('should return undefined for non-existent ID', () => {
    const group = { id: 'tg1', tools: [] };
    state.toolGroups = [group];
    expect(getToolGroup(state, 'tg999')).toBeUndefined();
  });
});

describe('getFilteredEvents', () => {
  let state;

  beforeEach(() => {
    state = createSessionState();
  });

  it('should return all events when filters are true', () => {
    state.events = [
      { type: 'query', prompt: 'test' },
      { type: 'message', content: 'response' },
      { type: 'tool_use', tool_name: 'Bash' },
    ];

    const filtered = getFilteredEvents(state);
    expect(filtered).toHaveLength(3);
  });

  it('should filter out events with false filters', () => {
    state.events = [
      { type: 'query', prompt: 'test' },
      { type: 'partial_message', delta: 'stream' }, // Default: false
      { type: 'message', content: 'response' },
    ];

    const filtered = getFilteredEvents(state);
    expect(filtered).toHaveLength(2);
    expect(filtered.find(e => e.type === 'partial_message')).toBeUndefined();
  });

  it('should handle event_type field (alternative)', () => {
    state.events = [
      { event_type: 'query', prompt: 'test' },
      { event_type: 'message', content: 'response' },
    ];

    const filtered = getFilteredEvents(state);
    expect(filtered).toHaveLength(2);
  });

  it('should include events with undefined filter (default to show)', () => {
    state.events = [{ type: 'unknown_event_type' }];

    const filtered = getFilteredEvents(state);
    expect(filtered).toHaveLength(1); // Shows by default
  });

  it('should respect custom filter changes', () => {
    state.events = [
      { type: 'query', prompt: 'test' },
      { type: 'message', content: 'response' },
    ];

    // Disable message filter
    state.eventTypeFilters.message = false;

    const filtered = getFilteredEvents(state);
    expect(filtered).toHaveLength(1);
    expect(filtered[0].type).toBe('query');
  });
});
