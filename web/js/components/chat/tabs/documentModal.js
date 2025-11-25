/**
 * Document Editor Modal Template
 * Displays and edits markdown documents with frontmatter support
 */

export function documentModalTemplate() {
  return /* html */`
    <!-- ========================================
         DOCUMENT EDITOR MODAL (DaisyUI)
         ======================================== -->
    <div
      x-show="showDocumentModal"
      x-cloak
      class="modal modal-open"
      @keydown.escape.window="closeDocumentModal()"
      @click.self="closeDocumentModal()"
    >
      <div class="modal-box w-11/12 max-w-5xl bg-base-200" @click.stop>
        <!-- Modal Header -->
        <div class="flex items-center justify-between mb-4">
          <!-- Left: Document info -->
          <div class="flex items-center gap-3">
            <div class="avatar placeholder">
              <div class="bg-primary text-primary-content rounded-lg w-10">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
              </div>
            </div>
            <div>
              <h3 class="font-bold text-lg" x-text="activeDocument?.docName || 'Document'"></h3>
              <p class="text-sm opacity-60">
                <span x-text="activeDocument?.docType || ''"></span>
                <span x-show="activeDocument?.projectName"> · <span x-text="activeDocument?.projectName"></span></span>
              </p>
            </div>
          </div>

          <!-- Right: Action buttons -->
          <div class="flex items-center gap-2">
            <!-- Save as Version (only in edit mode if document has version field, enabled when has changes) -->
            <button
              x-show="activeDocument?.isEditing && activeDocument?.frontmatter?.version"
              @click="saveDocumentAsVersion()"
              :disabled="activeDocument?.rawContent === activeDocument?.originalRawContent"
              class="btn btn-outline btn-sm gap-1"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"></path>
              </svg>
              New Version
            </button>

            <!-- Save (only in edit mode, enabled when has changes) -->
            <button
              x-show="activeDocument?.isEditing"
              @click="saveDocumentContent()"
              :disabled="activeDocument?.rawContent === activeDocument?.originalRawContent"
              class="btn btn-success btn-sm gap-1"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
              </svg>
              Save
            </button>

            <!-- Divider -->
            <div class="divider divider-horizontal"></div>

            <!-- Edit/Preview toggle -->
            <button
              @click="toggleDocumentEdit()"
              :class="activeDocument?.isEditing ? 'btn-ghost' : 'btn-primary'"
              class="btn btn-sm gap-1"
            >
              <svg x-show="!activeDocument?.isEditing" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
              </svg>
              <svg x-show="activeDocument?.isEditing" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
              </svg>
              <span x-text="activeDocument?.isEditing ? 'Preview' : 'Edit'"></span>
            </button>

            <!-- Close button -->
            <button
              @click="closeDocumentModal()"
              class="btn btn-sm btn-circle btn-ghost"
              title="Close (Esc)"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        </div>

        <!-- Modal Body -->
        <div class="max-h-[70vh] overflow-y-auto">
          <!-- View Mode -->
          <div
            x-show="activeDocument && !activeDocument.isEditing"
            class="prose max-w-none bg-white dark:bg-gray-900 p-6 rounded-lg"
          >
            <!-- Frontmatter -->
            <div
              x-show="activeDocument?.frontmatter && Object.keys(activeDocument.frontmatter).length > 0"
              class="text-xs font-mono text-gray-600 dark:text-gray-400 space-y-1 mb-6"
            >
              <template x-for="[key, value] in Object.entries(activeDocument?.frontmatter || {})" :key="key">
                <div class="flex gap-2">
                  <span class="font-semibold" x-text="key + ':'"></span>
                  <span x-text="Array.isArray(value) ? value.join(', ') : value"></span>
                </div>
              </template>
            </div>

            <!-- Content -->
            <div class="markdown-content text-gray-900 dark:text-gray-100" x-html="renderMarkdown(activeDocument?.content || '')"></div>
          </div>

          <!-- Edit Mode -->
          <div x-show="activeDocument && activeDocument.isEditing" class="space-y-4">
            <textarea
              id="document-modal-textarea"
              x-model="activeDocument.rawContent"
              class="textarea textarea-bordered w-full h-[60vh] font-mono text-sm"
              placeholder="Edit document content..."
            ></textarea>

            <!-- Versions List -->
            <div x-show="activeDocument?.versions?.length > 0" class="divider">Versions</div>
            <div x-show="activeDocument?.versions?.length > 0" class="flex flex-wrap gap-2">
              <template x-for="version in activeDocument?.versions || []" :key="version">
                <div class="badge badge-outline font-mono" x-text="version"></div>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}
