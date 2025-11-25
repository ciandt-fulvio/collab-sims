/**
 * Agents Tab Template
 * Displays list of available agents with active status
 */

export function agentsTabTemplate() {
  return /* html */`
    <!-- ========================================
         AGENTS TAB
         ======================================== -->
    <!-- Agents tab -->
    <div x-show="activeTab === 'agents'" class="p-4 space-y-3">
      <template x-if="agents.length > 0">
        <div class="space-y-2">
          <template x-for="agent in agents" :key="agent.name">
            <div
              class="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
              :class="{'border-l-4 border-l-purple-500 dark:border-l-purple-400': agent.name === agentName}"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100" x-text="agent.name"></h4>
                    <span x-show="agent.name === agentName" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400">
                      Active
                    </span>
                  </div>
                  <p class="text-xs text-gray-600 dark:text-gray-400 mt-1" x-text="agent.description || 'No description'"></p>
                </div>
              </div>
              <div class="pt-2 border-t border-gray-200 dark:border-gray-700 mt-2">
                <button
                  @click="viewAgentDetails(agent)"
                  class="px-3 py-1 text-xs bg-purple-600 dark:bg-purple-700 text-white rounded-lg hover:bg-purple-700 dark:hover:bg-purple-600 transition flex items-center gap-1"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                  </svg>
                  <span>View/Edit</span>
                </button>
              </div>
            </div>
          </template>
        </div>
      </template>
      <template x-if="agents.length === 0">
        <div class="text-center text-gray-400 dark:text-gray-500 py-8">
          <p class="text-sm">No agents available</p>
        </div>
      </template>
    </div>
  `;
}
