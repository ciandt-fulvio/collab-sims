/**
 * Events Panel Component
 * Handles event list display, filtering, and expansion
 */

import { getFilteredEvents } from '../../state/sessionState.js?v=4';

export function eventsPanel() {
  return {
    // Data
    events: [],

    // Track expanded events in Events tab
    expandedEvents: new Set(),

    // Event type filters (all enabled by default except partial_message)
    eventTypeFilters: {
      session_start: true,
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
      activity_card: true,
      system: true,
    },

    // Filter expansion state
    showEventFilters: false,

    // Toggle event expansion
    toggleEventExpansion(eventId) {
      if (this.expandedEvents.has(eventId)) {
        this.expandedEvents.delete(eventId);
      } else {
        this.expandedEvents.add(eventId);
      }
    },

    // Check if event is expanded
    isEventExpanded(eventId) {
      return this.expandedEvents.has(eventId);
    },

    // Toggle event type filter
    toggleEventTypeFilter(eventType) {
      this.eventTypeFilters[eventType] = !this.eventTypeFilters[eventType];
    },

    // Get filtered events
    getFilteredEvents() {
      return getFilteredEvents(this);
    },

    // Select all event type filters
    selectAllEventFilters() {
      Object.keys(this.eventTypeFilters).forEach(key => {
        this.eventTypeFilters[key] = true;
      });
    },

    // Deselect all event type filters
    deselectAllEventFilters() {
      Object.keys(this.eventTypeFilters).forEach(key => {
        this.eventTypeFilters[key] = false;
      });
    },

    // Reset events state
    resetEvents() {
      this.events = [];
      this.expandedEvents.clear();
    },
  };
}
