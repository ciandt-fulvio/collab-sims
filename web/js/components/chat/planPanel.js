/**
 * Plan Panel Component
 * Handles plan/todo display and state management
 */

import {
  getCurrentPlan,
  getPreviousPlans
} from '../../state/sessionState.js?v=4';

export function planPanel() {
  return {
    // Data
    plans: [],  // Array to store all plans (current and historical)

    // Track expanded plans in Plan tab
    expandedPlans: new Set(),

    // Get current plan (most recent)
    getCurrentPlan() {
      return getCurrentPlan(this);
    },

    // Get previous plans (all except current)
    getPreviousPlans() {
      return getPreviousPlans(this);
    },

    // Toggle plan expansion
    togglePlanExpansion(planIndex) {
      if (this.expandedPlans.has(planIndex)) {
        this.expandedPlans.delete(planIndex);
      } else {
        this.expandedPlans.add(planIndex);
      }
    },

    // Check if plan is expanded
    isPlanExpanded(planIndex) {
      return this.expandedPlans.has(planIndex);
    },

    // Reset plans state
    resetPlans() {
      this.plans = [];
      this.expandedPlans.clear();
    },
  };
}
