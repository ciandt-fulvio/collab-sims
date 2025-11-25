/**
 * Activities Tab Template
 * Displays activity execution results grouped by activity type
 * with expandable execution history
 */

export function activitiesTabTemplate() {
  return /* html */`
    <!-- ========================================
         ACTIVITIES TAB - Execution Results
         ======================================== -->
    <!-- Activities tab -->
    <div x-show="activeTab === 'activities'" x-init="$watch('activeTab', value => { if (value === 'activities' && projectName && !activityResults) loadActivityResults() })" class="p-4 space-y-3">
      <!-- Header -->
      <div x-show="projectName" class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <svg class="w-4 h-4 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
          </svg>
          <span>Activity Execution Results</span>
        </h3>
        <span x-show="activityResults" class="text-xs text-gray-500 dark:text-gray-400" x-text="\`\${activityResults?.activity_groups?.length || 0} types\`"></span>
      </div>

      <!-- Loading -->
      <div x-show="loadingActivityResults" class="text-center text-gray-400 dark:text-gray-500 py-8">
        <div class="inline-flex space-x-2 mb-4">
          <div class="w-3 h-3 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"></div>
          <div class="w-3 h-3 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
          <div class="w-3 h-3 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
        </div>
        <p class="text-sm">Loading activity results...</p>
      </div>

      <!-- Activity Groups with Collapsible Executions -->
      <div x-show="activityResults && !loadingActivityResults" class="space-y-2">
        <template x-if="activityResults?.activity_groups?.length > 0">
          <div class="space-y-2">
            <template x-for="group in activityResults.activity_groups || []" :key="group.activity_script">
              <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:border-yellow-300 dark:hover:border-yellow-600 transition">
                <button @click="toggleActivityGroupExpansion(group.activity_script)" class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
                  <div class="flex items-center gap-3 flex-1 text-left">
                    <svg class="w-4 h-4 transition-transform text-gray-500" :class="{'rotate-90': isActivityGroupExpanded(group.activity_script)}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                    <div class="flex-1">
                      <div class="flex items-center gap-2 mb-1">
                        <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100" x-text="group.activity_title || group.activity_script"></h4>
                        <span class="px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400">
                          <span x-text="group.executions?.length || 0"></span> execution<span x-show="group.executions?.length !== 1">s</span>
                        </span>
                      </div>
                      <p class="text-xs text-gray-600 dark:text-gray-400">
                        Latest: <span x-text="group.executions?.[0]?.created_at || 'N/A'"></span>
                      </p>
                    </div>
                  </div>
                </button>

                <!-- Executions List (Collapsed) -->
                <div x-show="isActivityGroupExpanded(group.activity_script)" x-collapse class="px-4 pb-4 space-y-2 border-t border-gray-200 dark:border-gray-700">
                  <template x-for="(execution, index) in group.executions || []" :key="execution.filename">
                    <div class="bg-gray-50 dark:bg-gray-900/30 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                      <div class="flex items-start justify-between mb-2">
                        <div class="flex-1">
                          <div class="flex items-center gap-2 mb-1">
                            <span class="text-sm font-medium text-gray-900 dark:text-gray-100">
                              Execution #<span x-text="group.executions.length - index"></span>
                            </span>
                            <span class="px-1.5 py-0.5 rounded text-xs font-medium" :class="{'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400': execution.status === 'completed', 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400': execution.status === 'running', 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400': execution.status === 'error'}" x-text="execution.status || 'unknown'"></span>
                          </div>
                          <div class="text-xs text-gray-600 dark:text-gray-400 space-y-0.5">
                            <div class="flex items-center gap-1">
                              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                              </svg>
                              <span x-text="execution.created_at"></span>
                            </div>
                            <div x-show="execution.metadata?.participants" class="flex items-center gap-1">
                              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                              </svg>
                              <span x-text="execution.metadata.participants"></span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
                        <button
                          @click="openDocument('activity_result', execution.filename.replace('.md', ''), projectName)"
                          class="px-3 py-1 text-xs bg-yellow-600 dark:bg-yellow-700 text-white rounded-lg hover:bg-yellow-700 dark:hover:bg-yellow-600 transition flex items-center gap-1"
                        >
                          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                          </svg>
                          <span>Edit result document</span>
                        </button>
                      </div>
                    </div>
                  </template>
                </div>
              </div>
            </template>
          </div>
        </template>
        <template x-if="!activityResults?.activity_groups || activityResults.activity_groups.length === 0">
          <div class="text-center text-gray-400 dark:text-gray-500 py-8">
            <p class="text-sm">No activity executions found for this project</p>
          </div>
        </template>
      </div>

      <!-- No Project Message -->
      <div x-show="!projectName" class="text-center text-gray-400 dark:text-gray-500 py-8">
        <p class="text-sm">No project associated with this session</p>
      </div>
    </div>
  `;
}
