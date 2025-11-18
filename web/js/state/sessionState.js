/**
 * Session state management
 * Provides factory for creating session state and update methods
 */

/**
 * Create initial session state
 */
export function createSessionState() {
  return {
    // Session data
    sessionId: null,
    messages: [],
    events: [],
    plans: [],
    approvals: [],
    toolGroups: [],
    currentToolGroupId: null,

    // Streaming state
    isStreaming: false,
    partialText: '',
    seenMessages: new Set(),

    // UI state
    expandedEvents: new Set(),
    expandedPlans: new Set(),

    // Metrics tracking
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

    // Event filters
    eventTypeFilters: {
      query: true,
      message: true,
      partial_message: false,
      tool_use: true,
      tool_result: true,
      plan: true,
      progress: true,
      complete: true,
      error: true,
      approval_request: true,
      approval_response: true,
      system: true,
      metrics: true,
    },
  };
}

/**
 * Reset session state (for new session)
 */
export function resetSessionState(state) {
  // Clear data arrays
  state.messages = [];
  state.events = [];
  state.plans = [];
  state.approvals = [];
  state.toolGroups = [];
  state.currentToolGroupId = null;
  state.partialText = '';
  state.seenMessages.clear();
  state.expandedEvents.clear();
  state.expandedPlans.clear();

  // Reset metrics
  state.metrics = {
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
    totalCost: 0,
    durationMs: 0,
    numTurns: 0,
    messagesCount: 0,
    toolsCount: 0,
  };
}

/**
 * Get current plan (most recent)
 */
export function getCurrentPlan(state) {
  return state.plans.length > 0 ? state.plans[state.plans.length - 1] : null;
}

/**
 * Get previous plans (all except the most recent)
 */
export function getPreviousPlans(state) {
  return state.plans.length > 1 ? state.plans.slice(0, -1).reverse() : [];
}

/**
 * Get current tool group
 */
export function getCurrentToolGroup(state) {
  if (!state.currentToolGroupId) return null;
  return state.toolGroups.find(g => g.id === state.currentToolGroupId);
}

/**
 * Get tool group by ID
 */
export function getToolGroup(state, groupId) {
  return state.toolGroups.find(g => g.id === groupId);
}

/**
 * Get filtered events based on event type filters
 */
export function getFilteredEvents(state) {
  return state.events.filter(event => {
    const eventType = event.type || event.event_type;
    return state.eventTypeFilters[eventType] !== false; // Show if undefined or true
  });
}
