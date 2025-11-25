/**
 * Task Tab Template
 * Displays current plan progress and previous plans
 * State management handled by planPanel.js
 */

export function taskTabTemplate() {
  return /* html */`
    <!-- ========================================
         TASK TAB (formerly Plan)
         Component: planPanel.js
         ======================================== -->
    <!-- Task tab -->
    <div x-show="activeTab === 'task'" class="p-4 space-y-4">
      <!-- Current Plan -->
      <div x-show="getCurrentPlan()" class="space-y-3">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Current Plan</h3>

        <!-- Progress bar -->
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 border-2 border-blue-300 dark:border-blue-600">
          <div class="flex justify-between text-sm mb-2 text-gray-900 dark:text-gray-100">
            <span class="font-semibold">Progress</span>
            <span x-text="\`\${getCurrentPlan()?.completed || 0}/\${getCurrentPlan()?.total_tasks || 0}\`"></span>
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              class="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all duration-300"
              :style="\`width: \${getCurrentPlan() ? (getCurrentPlan().completed / getCurrentPlan().total_tasks * 100) : 0}%\`"
            ></div>
          </div>
        </div>

        <!-- Current Tasks -->
        <div class="space-y-2">
          <template x-for="todo in getCurrentPlan()?.todos || []" :key="todo.content">
            <div
              class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
              :class="{
                'border-l-4 border-l-green-500 dark:border-l-green-400': todo.status === 'completed',
                'border-l-4 border-l-blue-500 dark:border-l-blue-400': todo.status === 'in_progress',
                'border-l-4 border-l-gray-300 dark:border-l-gray-600': todo.status === 'pending'
              }"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="text-sm font-medium text-gray-900 dark:text-gray-100" x-text="todo.content"></div>
                  <div class="text-xs text-gray-500 dark:text-gray-400 mt-1" x-text="todo.status"></div>
                </div>
                <div class="ml-2">
                  <span x-show="todo.status === 'completed'" class="text-green-500 dark:text-green-400">✓</span>
                  <span x-show="todo.status === 'in_progress'" class="text-blue-500 dark:text-blue-400">●</span>
                  <span x-show="todo.status === 'pending'" class="text-gray-400 dark:text-gray-500">○</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Previous Plans (collapsible) -->
      <div x-show="getPreviousPlans().length > 0" class="space-y-2">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Previous Plans</h3>
        <template x-for="(prevPlan, index) in getPreviousPlans()" :key="prevPlan.timestamp">
          <div class="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <!-- Collapsible header -->
            <div
              @click="togglePlanExpansion(index)"
              class="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition rounded-lg"
            >
              <div class="flex items-center gap-2">
                <!-- Chevron -->
                <svg
                  class="w-4 h-4 transition-transform text-gray-500"
                  :class="{'rotate-90': isPlanExpanded(index)}"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                </svg>
                <span class="text-xs text-gray-600 dark:text-gray-400">
                  Plan #<span x-text="getPreviousPlans().length - index"></span> -
                  <span x-text="\`\${prevPlan.completed}/\${prevPlan.total_tasks} completed\`"></span>
                </span>
              </div>
              <span class="text-xs text-gray-500 dark:text-gray-400" x-text="new Date(prevPlan.timestamp).toLocaleString()"></span>
            </div>

            <!-- Previous plan details (collapsible) -->
            <div x-show="isPlanExpanded(index)" x-transition class="px-3 pb-3 space-y-2">
              <template x-for="todo in prevPlan.todos || []" :key="todo.content">
                <div
                  class="bg-white dark:bg-gray-800 rounded-lg p-2 border border-gray-200 dark:border-gray-700 text-xs"
                  :class="{
                    'border-l-4 border-l-green-500 dark:border-l-green-400': todo.status === 'completed',
                    'border-l-4 border-l-blue-500 dark:border-l-blue-400': todo.status === 'in_progress',
                    'border-l-4 border-l-gray-300 dark:border-l-gray-600': todo.status === 'pending'
                  }"
                >
                  <div class="flex items-start justify-between">
                    <div class="flex-1 text-gray-900 dark:text-gray-100" x-text="todo.content"></div>
                    <div class="ml-2">
                      <span x-show="todo.status === 'completed'" class="text-green-500 dark:text-green-400">✓</span>
                      <span x-show="todo.status === 'in_progress'" class="text-blue-500 dark:text-blue-400">●</span>
                      <span x-show="todo.status === 'pending'" class="text-gray-400 dark:text-gray-500">○</span>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- No plans message -->
      <div x-show="plans.length === 0" class="text-center text-gray-400 dark:text-gray-500 py-8">
        <svg class="mx-auto h-12 w-12 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
        </svg>
        <p>No plan yet</p>
      </div>
    </div>
  `;
}
