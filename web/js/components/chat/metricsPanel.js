/**
 * Metrics Panel Component
 * Handles session metrics tracking and display
 */

export function metricsPanel() {
  return {
    // UI state
    showMetrics: false,  // Start collapsed to give more space to Plan panel

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

    // Real-time metrics tracking
    queryStartTime: null,
    durationTimer: null,
    isMetricsLive: false,

    // Accumulated metrics from completed queries
    accumulatedDurationMs: 0,
    accumulatedInputTokens: 0,
    accumulatedOutputTokens: 0,

    // Current query token estimates (reset on each new query)
    currentQueryInputTokens: 0,
    currentQueryOutputTokens: 0,

    // Start real-time duration timer
    startDurationTimer() {
      this.startDurationTimerFrom(Date.now());
    },

    // Start real-time duration timer from a specific start time
    startDurationTimerFrom(startTime) {
      // Stop any existing timer
      this.stopDurationTimer();

      // Record start time
      this.queryStartTime = startTime;
      console.log('⏱️ Timer started - queryStartTime:', startTime, 'accumulatedDurationMs:', this.accumulatedDurationMs);

      // Update duration every 100ms for smooth updates
      // Show accumulated duration + current query duration
      this.durationTimer = setInterval(() => {
        if (this.queryStartTime) {
          const now = Date.now();
          const currentQueryDuration = now - this.queryStartTime;
          this.metrics.durationMs = this.accumulatedDurationMs + currentQueryDuration;

          // Debug log on first tick to see values
          if (!this._firstTickLogged) {
            console.log('⏱️ Timer tick - now:', now, 'queryStartTime:', this.queryStartTime, 'currentQueryDuration:', currentQueryDuration, 'accumulated:', this.accumulatedDurationMs, 'total:', this.metrics.durationMs);
            this._firstTickLogged = true;
          }
        }
      }, 100);
    },

    // Stop real-time duration timer
    stopDurationTimer() {
      if (this.durationTimer) {
        clearInterval(this.durationTimer);
        this.durationTimer = null;
      }
      this.queryStartTime = null;
      this.isMetricsLive = false;
      this._firstTickLogged = false;
    },

    // Reset metrics to initial state
    resetMetrics() {
      this.metrics = {
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
        totalCost: 0,
        durationMs: 0,
        numTurns: 0,
        messagesCount: 0,
        toolsCount: 0,
      };
      this.accumulatedDurationMs = 0;
      this.accumulatedInputTokens = 0;
      this.accumulatedOutputTokens = 0;
      this.currentQueryInputTokens = 0;
      this.currentQueryOutputTokens = 0;
    },
  };
}
