/**
 * Event handlers for different event types from the SSE stream.
 * Each handler receives the component context and the event.
 */

/**
 * Truncate text at word/punctuation boundary, avoiding breaking words.
 * Tries to stay close to max_length characters but will cut at spaces or
 * punctuation marks instead of breaking words.
 */
function truncateSessionName(text, maxLength = 30) {
  if (!text || text.length <= maxLength) {
    return text.trim();
  }

  // Pattern for spaces and punctuation
  const punctuationPattern = /[\s.,!?;:\'"()\[\]{}\-–—]/;

  // Look backward from maxLength to find a space or punctuation
  for (let i = maxLength; i >= 0; i--) {
    if (punctuationPattern.test(text[i])) {
      return text.substring(0, i).trim();
    }
  }

  // If no punctuation found, return up to maxLength
  return text.substring(0, maxLength).trim();
}

/**
 * Estimate token count from text
 * Uses rough approximation: 1 token ≈ 4 characters
 * This matches OpenAI's rule of thumb for English text
 */
function estimateTokens(text) {
  if (!text) return 0;
  // Simple estimation: ~4 characters per token
  return Math.ceil(text.length / 4);
}

/**
 * Estimate cost from token counts
 * Uses Claude 3.5 Sonnet pricing:
 * - Input: $3 per million tokens ($0.000003 per token)
 * - Output: $15 per million tokens ($0.000015 per token)
 */
function estimateCost(inputTokens, outputTokens) {
  const inputCost = inputTokens * 0.000003;
  const outputCost = outputTokens * 0.000015;
  return inputCost + outputCost;
}

/**
 * Handle query event (user submitted a query)
 */
export function handleQueryEvent(context, event) {
  console.log('Query started:', event.prompt);

  // Only add user's query as a message when loading history or reconnecting
  // During live streaming, sendMessage() already added the user message
  if (event.prompt && context.isLoadingHistory) {
    context.addMessage('user', event.prompt, null, event.timestamp, event.event_id);
  }

  // Capture first message for session name (only once, only during live streaming)
  console.log('🔍 Query event - checking session name capture:', {
    hasPrompt: !!event.prompt,
    isStreaming: context.isStreaming,
    sessionNameCaptured: context.sessionNameCaptured,
    messagesLength: context.messages.length,
    willCapture: event.prompt && context.isStreaming && !context.sessionNameCaptured && context.messages.length <= 1
  });

  if (event.prompt && context.isStreaming && !context.sessionNameCaptured && context.messages.length <= 1) {
    const sessionName = truncateSessionName(event.prompt);
    console.log('📝 Capturing session name:', sessionName);
    context.api.updateSessionName(context.sessionId, sessionName)
      .then(() => {
        context.sessionName = sessionName;
        context.sessionNameCaptured = true;
        console.log('✅ Session name updated:', sessionName);
      })
      .catch(err => console.error('❌ Failed to update session name:', err));
  }

  // Reset current query token estimates when starting new query
  context.currentQueryInputTokens = 0;
  context.currentQueryOutputTokens = 0;

  // Estimate input tokens from user prompt
  if (event.prompt) {
    const estimatedTokens = estimateTokens(event.prompt);
    context.currentQueryInputTokens = estimatedTokens;

    // Display accumulated + current query tokens
    context.metrics.inputTokens = context.accumulatedInputTokens + context.currentQueryInputTokens;
    context.metrics.outputTokens = context.accumulatedOutputTokens + context.currentQueryOutputTokens;
    context.metrics.totalTokens = context.metrics.inputTokens + context.metrics.outputTokens;
    context.metrics.totalCost = estimateCost(context.metrics.inputTokens, context.metrics.outputTokens);
  }
}

/**
 * Handle partial message event (word-by-word streaming)
 * Only animates in chat during live streaming, but always logged to Events tab
 */
export function handlePartialMessageEvent(context, event) {
  // Only update chat animation during live streaming, not during history load
  if (context.isStreaming) {
    context.partialText += event.delta;
    context.scrollToBottom();
  }
  // Event is still added to events array by caller, so it appears in Events tab

  // Estimate output tokens from streamed text delta
  if (event.delta) {
    const estimatedTokens = estimateTokens(event.delta);
    context.currentQueryOutputTokens += estimatedTokens;

    // Display accumulated + current query tokens
    context.metrics.outputTokens = context.accumulatedOutputTokens + context.currentQueryOutputTokens;
    context.metrics.totalTokens = context.metrics.inputTokens + context.metrics.outputTokens;
    context.metrics.totalCost = estimateCost(context.metrics.inputTokens, context.metrics.outputTokens);
  }
}

/**
 * Handle message event (final assistant message)
 */
export function handleMessageEvent(context, event) {
  context.partialText = ''; // Clear partial text before adding final message

  // Only add message if it has content or thinking
  if (event.content || event.thinking) {
    context.addMessage('assistant', event.content, event.thinking, event.timestamp, event.event_id);
  }

  // Update metrics - increment message count
  context.metrics.messagesCount++;
}

/**
 * Handle tool_use event (agent is using a tool)
 */
export function handleToolUseEvent(context, event) {
  // Create or get current tool group
  if (!context.currentToolGroupId || context.getCurrentToolGroup()?.messageId !== event.originated_from_message_id) {
    // New turn - create new tool group
    const groupId = `tool_group_${Date.now()}_${Math.random()}`;
    context.currentToolGroupId = groupId;
    context.toolGroups.push({
      id: groupId,
      messageId: event.originated_from_message_id,
      tools: [],
      timestamp: event.timestamp || Date.now(),
      expanded: false
    });

    // Add to messages timeline
    context.messages.push({
      id: groupId,
      role: 'tool_group',
      tool_group_id: groupId,
      timestamp: event.timestamp || Date.now()
    });
  }

  // Add tool to current group
  const currentGroup = context.getCurrentToolGroup();
  if (currentGroup) {
    currentGroup.tools.push({
      use: event,
      result: null
    });
  }

  // Update metrics - increment tool count (exclude TodoWrite as it's internal)
  if (event.tool_name !== 'TodoWrite') {
    context.metrics.toolsCount++;
  }

  // Estimate input tokens from tool use parameters
  if (event.input) {
    const inputText = JSON.stringify(event.input);
    const estimatedTokens = estimateTokens(inputText);
    context.currentQueryInputTokens += estimatedTokens;

    // Display accumulated + current query tokens
    context.metrics.inputTokens = context.accumulatedInputTokens + context.currentQueryInputTokens;
    context.metrics.totalTokens = context.metrics.inputTokens + context.metrics.outputTokens;
    context.metrics.totalCost = estimateCost(context.metrics.inputTokens, context.metrics.outputTokens);
  }
}

/**
 * Handle tool_result event (tool execution completed)
 */
export function handleToolResultEvent(context, event) {
  // Find tool in groups and update with result
  for (const group of context.toolGroups) {
    const tool = group.tools.find(t => t.use.tool_use_id === event.tool_use_id);
    if (tool) {
      tool.result = event;
      break;
    }
  }

  // Estimate output tokens from tool result
  if (event.output) {
    const outputText = typeof event.output === 'string' ? event.output : JSON.stringify(event.output);
    const estimatedTokens = estimateTokens(outputText);
    context.currentQueryOutputTokens += estimatedTokens;

    // Display accumulated + current query tokens
    context.metrics.outputTokens = context.accumulatedOutputTokens + context.currentQueryOutputTokens;
    context.metrics.totalTokens = context.metrics.inputTokens + context.metrics.outputTokens;
    context.metrics.totalCost = estimateCost(context.metrics.inputTokens, context.metrics.outputTokens);
  }
}

/**
 * Handle plan event (agent created or updated a plan)
 */
export function handlePlanEvent(context, event) {
  // Check if this is a new plan or an update to the current plan
  const currentPlan = context.getCurrentPlan();

  // Determine if it's a new plan by comparing task content
  let isNewPlan = false;
  if (!currentPlan) {
    isNewPlan = true;
  } else {
    // Compare task content - if tasks are substantially different, it's a new plan
    const currentTasks = currentPlan.todos?.map(t => t.content).sort().join('|') || '';
    const newTasks = event.todos?.map(t => t.content).sort().join('|') || '';
    isNewPlan = currentTasks !== newTasks;
  }

  if (isNewPlan) {
    // New plan - add it to the array
    context.plans.push(event);

    // Auto-switch to task tab when a new plan starts (only during live streaming)
    if (context.isStreaming && context.activeTab !== 'task') {
      context.activeTab = 'task';
    }
  } else {
    // Update to existing plan - replace the current plan
    context.plans[context.plans.length - 1] = event;
  }
}

/**
 * Handle approval_request event (tool requires approval)
 */
export function handleApprovalRequestEvent(context, event) {
  const approval = {
    id: event.tool_use_id,
    tool_use_id: event.tool_use_id,
    tool_name: event.tool_name,
    tool_input: event.tool_input,
    risk_level: event.risk_level || 'medium',
    status: event.status || 'pending',
    created_at: event.created_at || event.timestamp,
    timestamp: event.timestamp,
  };

  // Add to approvals list if not already there
  const existing = context.approvals.find(a => a.id === approval.id);
  if (!existing) {
    context.approvals.push(approval);
    console.log('Approval request added:', approval);

    // Switch to approvals tab if not already there (only during live streaming)
    if (context.isStreaming && context.activeTab !== 'approvals') {
      context.activeTab = 'approvals';
    }
  }
}

/**
 * Handle approval_response event (user approved/rejected)
 */
export function handleApprovalResponseEvent(context, event) {
  const index = context.approvals.findIndex(a => a.id === event.tool_use_id);
  if (index !== -1) {
    // Remove from pending approvals
    context.approvals.splice(index, 1);
    console.log('Approval resolved:', event.tool_use_id, event.approved ? 'approved' : 'rejected');
  }
}

/**
 * Handle complete event (query execution completed)
 */
export function handleCompleteEvent(context, event) {
  context.isStreaming = false;

  // Stop real-time duration timer
  if (context.stopDurationTimer) {
    context.stopDurationTimer();
  }

  // Accumulate metrics from this completed query
  // The event contains per-query data, so we add it to the session totals
  if (event.usage) {
    const queryInputTokens = event.usage.input_tokens || 0;
    const queryOutputTokens = event.usage.output_tokens || 0;

    // Add this query's tokens to accumulated totals
    context.accumulatedInputTokens += queryInputTokens;
    context.accumulatedOutputTokens += queryOutputTokens;

    // Update displayed metrics with accumulated totals
    context.metrics.inputTokens = context.accumulatedInputTokens;
    context.metrics.outputTokens = context.accumulatedOutputTokens;
    context.metrics.totalTokens = context.metrics.inputTokens + context.metrics.outputTokens;

    // Recalculate cost based on accumulated tokens
    context.metrics.totalCost = estimateCost(context.metrics.inputTokens, context.metrics.outputTokens);
  }

  if (event.duration_ms) {
    // Add this query's duration to accumulated total
    context.accumulatedDurationMs += event.duration_ms;
    context.metrics.durationMs = context.accumulatedDurationMs;
  }

  if (event.num_turns) {
    context.metrics.numTurns = event.num_turns;
  }

  // Focus input after streaming completes so user can respond quickly
  context.focusInput();
}

/**
 * Handle metrics event (periodic metrics update during execution)
 */
export function handleMetricsEvent(context, event) {
  // Update metrics with live data
  if (event.input_tokens !== undefined) {
    context.metrics.inputTokens = event.input_tokens;
  }
  if (event.output_tokens !== undefined) {
    context.metrics.outputTokens = event.output_tokens;
  }
  context.metrics.totalTokens = context.metrics.inputTokens + context.metrics.outputTokens;

  if (event.total_cost_usd !== null && event.total_cost_usd !== undefined) {
    context.metrics.totalCost = event.total_cost_usd;
  }
  if (event.duration_ms !== undefined) {
    context.metrics.durationMs = event.duration_ms;
  }
}

/**
 * Handle error event (something went wrong)
 */
export function handleErrorEvent(context, event) {
  console.error('Agent error:', event);
  context.isStreaming = false;
  alert(`Error: ${event.error}`);
}

/**
 * Handle activity card event - displays interactive activity card in chat
 */
export function handleActivityCardEvent(context, event) {
  console.log('Activity card event:', event.activity_title);

  // Add the activity card event to messages for rendering
  // The card will be rendered by the chat HTML template
  const cardMessage = {
    id: event.event_id || `activity-card-${Date.now()}-${Math.random()}`,
    role: 'activity_card',
    activityData: {
      project_name: event.project_name,
      stage_title: event.stage_title,
      activity_id: event.activity_id,
      activity_title: event.activity_title,
      activity_description: event.activity_description,
      activity_script: event.activity_script,
      activity_required: event.activity_required,
      activity_completed: event.activity_completed,
      verifications: event.verifications || [],
    },
    timestamp: event.timestamp || new Date().toISOString(),
    event_id: event.event_id,
  };

  context.messages.push(cardMessage);
  context.scrollToBottom();
}

/**
 * Main event dispatcher - routes events to specific handlers
 */
export function dispatchEvent(context, event) {
  const eventType = event.type || event.event_type;

  // Map of event types to handlers
  const handlers = {
    'query': handleQueryEvent,
    'partial_message': handlePartialMessageEvent,
    'message': handleMessageEvent,
    'tool_use': handleToolUseEvent,
    'tool_result': handleToolResultEvent,
    'plan': handlePlanEvent,
    'approval_request': handleApprovalRequestEvent,
    'approval_response': handleApprovalResponseEvent,
    'complete': handleCompleteEvent,
    'metrics': handleMetricsEvent,
    'error': handleErrorEvent,
    'activity_card': handleActivityCardEvent,
  };

  // Call specific handler if available
  const handler = handlers[eventType];
  if (handler) {
    handler(context, event);
  } else {
    console.log('Unknown event type:', eventType, event);
  }
}
