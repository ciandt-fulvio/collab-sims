/**
 * Events Tab Template
 * Displays filtered event stream with expandable details
 * State management handled by eventsPanel.js
 */

export function eventsTabTemplate() {
  return /* html */`
    <!-- ========================================
         EVENTS TAB
         Component: eventsPanel.js
         ======================================== -->
    <!-- Events tab -->
    <div x-show="activeTab === 'events'" class="p-4 space-y-3">
    <!-- Filter bar -->
    <div class="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <!-- Collapsible header -->
      <div
        @click="showEventFilters = !showEventFilters"
        class="flex items-center gap-2 p-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition rounded-lg"
      >
        <!-- Chevron -->
        <svg
          class="w-4 h-4 transition-transform text-gray-500"
          :class="{'rotate-90': showEventFilters}"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
        </svg>
        <span class="font-semibold text-gray-700 dark:text-gray-300 text-xs">Filters</span>
      </div>

      <!-- Checkboxes (collapsible) -->
      <div x-show="showEventFilters" x-transition class="px-3 pb-3 pt-0">
        <div class="flex items-center gap-3 flex-wrap text-xs pt-2 border-t border-gray-200 dark:border-gray-700">

          <!-- All/None buttons (only visible when expanded) -->
          <div class="flex items-center gap-1">
            <button
              @click="selectAllEventFilters()"
              class="px-2 py-1 text-xs rounded bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800 transition"
            >
              All
            </button>
            <button
              @click="deselectAllEventFilters()"
              class="px-2 py-1 text-xs rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
            >
              None
            </button>
          </div>

          <span class="text-gray-400">|</span>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.message" class="rounded">
          <span>Messages</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.tool_use" class="rounded">
          <span>Tool Use</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.tool_result" class="rounded">
          <span>Tool Result</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.partial_message" class="rounded">
          <span>Partial Messages</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.complete" class="rounded">
          <span>Complete</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.error" class="rounded">
          <span>Errors</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.query" class="rounded">
          <span>Queries</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.system" class="rounded">
          <span>System</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.plan" class="rounded">
          <span>Plans</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.progress" class="rounded">
          <span>Progress</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.approval_request" class="rounded">
          <span>Approval Requests</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.approval_response" class="rounded">
          <span>Approval Responses</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.session_start" class="rounded">
          <span>Session Start</span>
        </label>

        <label class="flex items-center gap-1.5 cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200">
          <input type="checkbox" x-model="eventTypeFilters.activity_card" class="rounded">
          <span>Activity Cards</span>
        </label>
        </div>
      </div>
    </div>

    <!-- Events list -->
    <template x-for="event in getFilteredEvents().slice().reverse()" :key="event.id">
      <div
        class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 text-xs overflow-hidden"
      >
        <!-- Compact header (always visible) - clickable -->
        <div
          @click="toggleEventExpansion(event.id)"
          class="p-3 cursor-pointer hover:bg-gray-100/50 dark:hover:bg-gray-700/30 transition flex items-center justify-between"
        >
          <div class="flex items-center gap-2 flex-1 min-w-0">
            <!-- Expand/collapse chevron -->
            <svg
              class="w-4 h-4 text-gray-400 dark:text-gray-500 flex-shrink-0 transition-transform"
              :class="{'rotate-90': isEventExpanded(event.id)}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>

            <!-- Event type badge -->
            <span
              class="px-2 py-1 rounded text-white font-medium text-xs flex-shrink-0"
              :class="{
                'bg-blue-500': event.type === 'query' || event.type === 'start',
                'bg-green-500': event.type === 'message',
                'bg-purple-500': event.type === 'partial_message',
                'bg-orange-500': event.type === 'tool_use',
                'bg-emerald-600': event.type === 'tool_result',
                'bg-yellow-500': event.type === 'plan',
                'bg-cyan-500': event.type === 'system',
                'bg-indigo-500': event.type === 'session_start',
                'bg-slate-500': event.type === 'session_end',
                'bg-teal-500': event.type === 'progress',
                'bg-gray-500': event.type === 'complete',
                'bg-red-500': event.type === 'error',
                'bg-pink-500': event.type === 'approval_request',
                'bg-lime-500': event.type === 'approval_response',
                'bg-amber-500': event.type === 'activity_card'
              }"
              x-text="event.type"
            ></span>

            <!-- Compact summary -->
            <span
              class="text-gray-700 dark:text-gray-300 truncate flex-1"
              x-text="getEventSummary(event)"
            ></span>
          </div>

          <!-- Timestamp -->
          <span
            class="text-gray-500 dark:text-gray-400 text-xs ml-2 flex-shrink-0"
            x-text="new Date(event.timestamp).toLocaleTimeString()"
          ></span>
        </div>

        <!-- Full JSON (expanded only) -->
        <div
          x-show="isEventExpanded(event.id)"
          x-transition
          class="p-3 pt-3 border-t border-gray-200 dark:border-gray-700 select-text"
        >
          <pre
            class="text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap break-words text-xs"
            x-text="JSON.stringify(event, null, 2)"
          ></pre>
        </div>
      </div>
    </template>

    <div x-show="events.length === 0" class="text-center text-gray-400 dark:text-gray-500 py-8">
      No events yet
    </div>
  </div>
  `;
}
