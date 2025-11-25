/**
 * Metrics Panel Template
 * Displays session metrics (tokens, cost, duration, activity)
 * State management handled by metricsPanel.js
 */

export function metricsPanelTemplate() {
  return /* html */`
    <!-- ========================================
         METRICS PANEL (Bottom, Compact)
         Component: metricsPanel.js
         ======================================== -->
    <!-- Metrics Panel -->
    <div class="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 border-t border-gray-200 dark:border-gray-700 p-3 flex-shrink-0">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
          </svg>
          Session Metrics
        </h3>
        <button
          @click="showMetrics = !showMetrics"
          class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition"
        >
          <svg
            class="w-4 h-4 transition-transform"
            :class="{'rotate-180': showMetrics}"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
          </svg>
        </button>
      </div>

      <!-- Compact view when collapsed -->
      <div x-show="!showMetrics" class="flex items-center justify-around text-xs text-gray-600 dark:text-gray-400 mt-2">
        <div class="flex items-center gap-1" :class="{'text-blue-600 dark:text-blue-400': isMetricsLive}">
          <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span class="font-bold font-mono inline-block min-w-[3.5rem] text-right" x-text="(metrics.durationMs / 1000).toFixed(1) + 's'">0.0s</span>
          <span x-show="isMetricsLive" class="text-blue-500 dark:text-blue-400 w-2 flex-shrink-0">●</span>
        </div>
        <div class="flex items-center gap-1">
          <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"></path>
          </svg>
          <span class="font-bold font-mono inline-block min-w-[3rem] text-right" x-text="(metrics.totalTokens / 1000).toFixed(1) + 'K'">0.0K</span>
        </div>
        <div class="flex items-center gap-1 text-green-600 dark:text-green-400">
          <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <span class="font-bold font-mono inline-block min-w-[4.5rem] text-right" x-text="'$' + metrics.totalCost.toFixed(4)">$0.0000</span>
        </div>
      </div>

      <!-- Full detailed view when expanded -->
      <div x-show="showMetrics" x-collapse.duration.200ms class="grid grid-cols-2 gap-2 mt-3">
        <!-- Tokens -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 hover:scale-[1.02]">
          <div class="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"></path>
            </svg>
            Tokens
          </div>
          <div class="text-xl font-bold text-gray-900 dark:text-gray-100 transition-all duration-300" x-text="metrics.totalTokens.toLocaleString()">0</div>
          <div class="text-xs text-gray-600 dark:text-gray-400 mt-1 space-y-0.5">
            <div class="flex justify-between">
              <span>In:</span>
              <span class="font-medium transition-all duration-300" x-text="metrics.inputTokens.toLocaleString()">0</span>
            </div>
            <div class="flex justify-between">
              <span>Out:</span>
              <span class="font-medium transition-all duration-300" x-text="metrics.outputTokens.toLocaleString()">0</span>
            </div>
          </div>
        </div>

        <!-- Cost -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 hover:scale-[1.02]">
          <div class="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            Cost
          </div>
          <div class="text-xl font-bold text-green-600 dark:text-green-400 transition-all duration-300">
            $<span x-text="metrics.totalCost.toFixed(4)">0.0000</span>
          </div>
          <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">
            USD
          </div>
        </div>

        <!-- Duration -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 hover:scale-[1.02]" :class="{'pulse-live': isMetricsLive}">
          <div class="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            Duration
            <span x-show="isMetricsLive" class="text-blue-500 dark:text-blue-400 font-semibold ml-1">●</span>
          </div>
          <div class="text-xl font-bold text-blue-600 dark:text-blue-400 transition-all duration-300">
            <span x-text="(metrics.durationMs / 1000).toFixed(1)">0.0</span>s
          </div>
          <div class="text-xs text-gray-600 dark:text-gray-400 mt-1">
            <span class="transition-all duration-300" x-text="metrics.numTurns">0</span> turn<span x-show="metrics.numTurns !== 1">s</span>
          </div>
        </div>

        <!-- Activity -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-all duration-200 hover:scale-[1.02]">
          <div class="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
            </svg>
            Activity
          </div>
          <div class="text-xs text-gray-700 dark:text-gray-300 space-y-0.5">
            <div class="flex justify-between">
              <span>Messages:</span>
              <span class="font-bold text-base transition-all duration-300" x-text="metrics.messagesCount">0</span>
            </div>
            <div class="flex justify-between">
              <span>Tools:</span>
              <span class="font-bold text-base transition-all duration-300" x-text="metrics.toolsCount">0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}
