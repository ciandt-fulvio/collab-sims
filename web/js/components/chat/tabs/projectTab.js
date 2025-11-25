/**
 * Project Tab Template
 * Displays process progress with stages and activities
 */

export function projectTabTemplate() {
  return /* html */`
    <!-- ========================================
         PROJECT TAB - Process Progress
         ======================================== -->
    <!-- Project tab -->
    <div
      x-show="activeTab === 'project'"
      x-init="
        $watch('activeTab', value => { if (value === 'project' && projectName && !processProgress) loadProcessProgress() });
        $watch('projectName', value => { if (value && activeTab === 'project' && !processProgress) loadProcessProgress() });
      "
      class="p-4 space-y-3"
    >
      <!-- Loading -->
      <div x-show="loadingProcessProgress" class="text-center text-gray-400 dark:text-gray-500 py-8">
        <div class="inline-flex space-x-2 mb-4">
          <div class="w-3 h-3 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"></div>
          <div class="w-3 h-3 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
          <div class="w-3 h-3 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
        </div>
        <p class="text-sm">Loading process progress...</p>
      </div>

      <!-- Process Progress -->
      <div x-show="processProgress && !loadingProcessProgress" class="space-y-4">
        <!-- Overall Progress -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
          <div class="flex justify-between text-sm mb-2 text-gray-900 dark:text-gray-100">
            <span class="font-semibold">Overall Progress</span>
            <span x-text="\`\${calculateTotalCompleted(processProgress)}/\${calculateTotalActivities(processProgress)} activities\`"></span>
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div class="bg-green-600 dark:bg-green-500 h-2 rounded-full transition-all duration-300" :style="\`width: \${calculateProgressPercentage(processProgress)}%\`"></div>
          </div>
        </div>

        <!-- Stages -->
        <template x-for="(stage, stageIndex) in processProgress?.stages || []" :key="stage.id">
          <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:border-green-300 dark:hover:border-green-600 transition">
            <button @click="toggleStageExpansion(stage.id)" class="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
              <div class="flex items-center gap-3">
                <svg class="w-4 h-4 transition-transform text-gray-500" :class="{'rotate-90': isStageExpanded(stage.id)}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                </svg>
                <div class="text-left">
                  <h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100" x-text="stage.title"></h4>
                  <p class="text-xs text-gray-500 dark:text-gray-400" x-text="stage.description"></p>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-xs text-gray-500 dark:text-gray-400">
                  <span x-text="stage.completion_count || 0"></span>/<span x-text="stage.total_activities || 0"></span>
                </span>
                <div class="w-16 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div class="h-full bg-green-500 dark:bg-green-400 transition-all" :style="\`width: \${((stage.completion_count || 0) / (stage.total_activities || 1)) * 100}%\`"></div>
                </div>
              </div>
            </button>

            <!-- Activities -->
            <div x-show="isStageExpanded(stage.id)" x-collapse class="px-4 pb-4 space-y-2">
              <template x-for="activity in stage.activities || []" :key="activity.id">
                <div @click="viewActivityOutputs(activity)" class="flex items-start gap-3 p-3 rounded bg-gray-50 dark:bg-gray-900/30 border border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800/50 transition" :class="{'border-l-4 border-l-green-500 dark:border-l-green-400': activity.completed, 'border-l-4 border-l-gray-300 dark:border-l-gray-600': !activity.completed}">
                  <div class="flex-shrink-0 mt-0.5">
                    <span x-show="activity.completed" class="text-green-500 dark:text-green-400 text-lg">✓</span>
                    <span x-show="!activity.completed" class="text-gray-300 dark:text-gray-600 text-lg">○</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <h5 class="text-sm font-medium text-gray-900 dark:text-gray-100" x-text="activity.title"></h5>
                      <span x-show="activity.required" class="px-1.5 py-0.5 rounded text-xs font-medium bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400">Required</span>
                      <span x-show="!activity.required" class="px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">Optional</span>
                    </div>
                    <p class="text-xs text-gray-600 dark:text-gray-400" x-text="activity.description"></p>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- No Project Message -->
      <div x-show="!projectName" class="text-center text-gray-400 dark:text-gray-500 py-8">
        <p class="text-sm">No project associated with this session</p>
      </div>

      <!-- No Process Type Message -->
      <div x-show="projectName && !processProgress && !loadingProcessProgress" class="text-center text-gray-400 dark:text-gray-500 py-8">
        <p class="text-sm">This project does not have a process type defined</p>
      </div>
    </div>
  `;
}
