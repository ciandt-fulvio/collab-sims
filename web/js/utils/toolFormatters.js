/**
 * Tool input/output formatters for displaying tool execution details.
 * Each formatter returns HTML strings for rendering in the UI.
 */

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Tool-specific input formatters
 */
const ToolInputFormatters = {
  Bash(input) {
    const command = input.command || input;
    return `<div class="font-mono text-gray-800 dark:text-gray-200"><span class="text-blue-600 dark:text-blue-400">$</span> ${escapeHtml(command)}</div>`;
  },

  Write(input) {
    const filePath = input.file_path || '';
    const content = input.content || '';
    const lines = content.split('\n').length;
    return `<div class="space-y-2">
      <div class="text-gray-700 dark:text-gray-300"><span class="text-purple-600 dark:text-purple-400">📝</span> ${escapeHtml(filePath)} <span class="text-gray-500 dark:text-gray-400 text-xs">(${lines} lines)</span></div>
      <pre class="font-mono text-gray-800 dark:text-gray-200 text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">${escapeHtml(content)}</pre>
    </div>`;
  },

  Read(input) {
    return `<div class="text-gray-700 dark:text-gray-300"><span class="text-green-600 dark:text-green-400">📖</span> ${escapeHtml(input.file_path || '')}</div>`;
  },

  Edit(input) {
    const filePath = input.file_path || '';
    const oldLines = (input.old_string || '').split('\n').length;
    const newLines = (input.new_string || '').split('\n').length;
    const replaceAll = input.replace_all;

    return `<div class="space-y-2">
      <div class="text-gray-700 dark:text-gray-300">
        <span class="text-yellow-600 dark:text-yellow-400">✏️</span> ${escapeHtml(filePath)}
        <span class="text-gray-500 dark:text-gray-400 text-xs ml-2">(${oldLines} → ${newLines} lines${replaceAll ? ', replace all' : ''})</span>
      </div>
      <details class="text-xs">
        <summary class="cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">Show diff</summary>
        <div class="mt-2 space-y-2">
          <div class="bg-red-50 dark:bg-red-900/20 p-2 rounded">
            <div class="text-red-700 dark:text-red-300 font-semibold mb-1">- Old string:</div>
            <pre class="font-mono text-red-800 dark:text-red-200 whitespace-pre-wrap max-h-40 overflow-y-auto">${escapeHtml(input.old_string || '')}</pre>
          </div>
          <div class="bg-green-50 dark:bg-green-900/20 p-2 rounded">
            <div class="text-green-700 dark:text-green-300 font-semibold mb-1">+ New string:</div>
            <pre class="font-mono text-green-800 dark:text-green-200 whitespace-pre-wrap max-h-40 overflow-y-auto">${escapeHtml(input.new_string || '')}</pre>
          </div>
        </div>
      </details>
    </div>`;
  },

  Runtime(input) {
    const content = input.dockerfile_content || '';
    const lines = content.split('\n').length;
    return `<div class="space-y-2">
      <div class="text-gray-700 dark:text-gray-300"><span class="text-orange-600 dark:text-orange-400">🐳</span> Dockerfile <span class="text-gray-500 dark:text-gray-400 text-xs">(${lines} lines)</span></div>
      <pre class="font-mono text-gray-800 dark:text-gray-200 text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">${escapeHtml(content)}</pre>
    </div>`;
  }
};

/**
 * Tool-specific output formatters
 */
export const ToolOutputFormatters = {
  Bash(output) {
    // Parse if it's a string that looks like JSON
    let parsedOutput = output;
    if (typeof output === 'string') {
      try {
        parsedOutput = JSON.parse(output);
      } catch (e) {
        // Not JSON, use as-is
      }
    }

    // Extract text from array format [{ type: "text", text: "..." }]
    if (Array.isArray(parsedOutput) && parsedOutput[0]?.type === 'text') {
      parsedOutput = parsedOutput[0].text;
    }

    if (typeof parsedOutput === 'object' && parsedOutput.stdout !== undefined) {
      const stdout = parsedOutput.stdout || '';
      const stderr = parsedOutput.stderr || '';
      const exitCode = parsedOutput.exit_code ?? parsedOutput.exitCode ?? 0;

      let html = '';
      if (stdout) {
        html += `<div class="mb-2"><div class="text-xs text-gray-600 dark:text-gray-400 mb-1">stdout:</div><pre class="font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">${escapeHtml(stdout)}</pre></div>`;
      }
      if (stderr) {
        html += `<div class="mb-2"><div class="text-xs text-red-600 dark:text-red-400 mb-1">stderr:</div><pre class="font-mono text-red-700 dark:text-red-300 whitespace-pre-wrap">${escapeHtml(stderr)}</pre></div>`;
      }
      html += `<div class="text-xs ${exitCode === 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">exit code: ${exitCode}</div>`;
      return html;
    }

    // Plain text bash output
    if (typeof parsedOutput === 'string') {
      return `<pre class="font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">${escapeHtml(parsedOutput)}</pre>`;
    }

    return `<pre class="font-mono text-gray-800 dark:text-gray-200">${escapeHtml(JSON.stringify(parsedOutput, null, 2))}</pre>`;
  },

  Write(output) {
    // Parse if it's a string that looks like JSON
    let parsedOutput = output;
    if (typeof output === 'string') {
      try {
        parsedOutput = JSON.parse(output);
      } catch (e) {
        // Not JSON, use as-is
      }
    }

    // Extract text from array format
    if (Array.isArray(parsedOutput) && parsedOutput[0]?.type === 'text') {
      parsedOutput = parsedOutput[0].text;
    }

    if (typeof parsedOutput === 'string' && parsedOutput.includes('File written:')) {
      const match = parsedOutput.match(/File written: (.+)/);
      if (match) {
        return `<div class="text-green-600 dark:text-green-400">✓ ${escapeHtml(match[1])}</div>`;
      }
    }

    if (typeof parsedOutput === 'string') {
      return `<pre class="font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">${escapeHtml(parsedOutput)}</pre>`;
    }

    return `<pre class="font-mono text-gray-800 dark:text-gray-200">${escapeHtml(JSON.stringify(parsedOutput, null, 2))}</pre>`;
  },

  Read(output) {
    // Parse if it's a string that looks like JSON
    let parsedOutput = output;
    if (typeof output === 'string') {
      try {
        parsedOutput = JSON.parse(output);
      } catch (e) {
        // Not JSON, use as-is
      }
    }

    // Extract text from array format
    if (Array.isArray(parsedOutput) && parsedOutput[0]?.type === 'text') {
      parsedOutput = parsedOutput[0].text;
    }

    if (typeof parsedOutput === 'string') {
      const lines = parsedOutput.split('\n').length;
      return `<div class="space-y-2">
        <div class="text-green-600 dark:text-green-400 text-xs">✓ Read ${lines} lines</div>
        <pre class="font-mono text-gray-800 dark:text-gray-200 text-xs whitespace-pre-wrap max-h-60 overflow-y-auto">${escapeHtml(parsedOutput)}</pre>
      </div>`;
    }

    return `<pre class="font-mono text-gray-800 dark:text-gray-200">${escapeHtml(JSON.stringify(parsedOutput, null, 2))}</pre>`;
  },

  Edit(output) {
    // Parse if it's a string that looks like JSON
    let parsedOutput = output;
    if (typeof output === 'string') {
      try {
        parsedOutput = JSON.parse(output);
      } catch (e) {
        // Not JSON, use as-is
      }
    }

    // Extract text from array format
    if (Array.isArray(parsedOutput) && parsedOutput[0]?.type === 'text') {
      parsedOutput = parsedOutput[0].text;
    }

    if (typeof parsedOutput === 'string') {
      // SDK's Edit tool returns "The file X has been updated. Here's the result of running `cat -n`..."
      if (parsedOutput.includes('has been updated')) {
        // Extract file path
        const fileMatch = parsedOutput.match(/The file (.+?) has been updated/);
        const filePath = fileMatch ? fileMatch[1] : 'file';

        // Check if there's cat -n output
        if (parsedOutput.includes('cat -n')) {
          return `<div class="space-y-2">
            <div class="text-green-600 dark:text-green-400">✓ ${escapeHtml(filePath)} updated</div>
            <details class="text-xs">
              <summary class="cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">Show updated snippet</summary>
              <pre class="mt-2 font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap max-h-60 overflow-y-auto bg-gray-50 dark:bg-gray-800 p-2 rounded">${escapeHtml(parsedOutput)}</pre>
            </details>
          </div>`;
        }

        return `<div class="text-green-600 dark:text-green-400">✓ ${escapeHtml(filePath)} updated</div>`;
      }

      // Fallback for simple "File edited successfully" messages
      if (parsedOutput.includes('successfully') || parsedOutput.includes('edited')) {
        return `<div class="text-green-600 dark:text-green-400">✓ ${escapeHtml(parsedOutput)}</div>`;
      }

      return `<pre class="font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">${escapeHtml(parsedOutput)}</pre>`;
    }

    return `<pre class="font-mono text-gray-800 dark:text-gray-200">${escapeHtml(JSON.stringify(parsedOutput, null, 2))}</pre>`;
  },

  Runtime(output) {
    // Parse if it's a string that looks like JSON
    let parsedOutput = output;
    if (typeof output === 'string') {
      try {
        parsedOutput = JSON.parse(output);
      } catch (e) {
        // Not JSON, use as-is
      }
    }

    // Extract text from array format
    if (Array.isArray(parsedOutput) && parsedOutput[0]?.type === 'text') {
      parsedOutput = parsedOutput[0].text;
    }

    if (typeof parsedOutput === 'string') {
      if (parsedOutput.includes('Container ID:')) {
        const lines = parsedOutput.split('\n');
        return `<div class="space-y-1">${lines.map(line =>
          `<div class="text-gray-700 dark:text-gray-300">${escapeHtml(line)}</div>`
        ).join('')}</div>`;
      }

      return `<pre class="font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">${escapeHtml(parsedOutput)}</pre>`;
    }

    return `<pre class="font-mono text-gray-800 dark:text-gray-200">${escapeHtml(JSON.stringify(parsedOutput, null, 2))}</pre>`;
  }
};

/**
 * Format tool input for display
 */
export function formatToolInput(toolName, input) {
  if (!input) return '<span class="text-gray-500 dark:text-gray-400">{}</span>';

  // Normalize tool name (remove mcp__sims__ prefix)
  const normalizedName = toolName.replace(/^mcp__sims__/, '');

  // Use specific formatter if available
  const formatter = ToolInputFormatters[normalizedName];
  if (formatter) {
    return formatter(input);
  }

  // Default: pretty JSON
  return `<pre class="font-mono text-gray-800 dark:text-gray-200">${escapeHtml(JSON.stringify(input, null, 2))}</pre>`;
}

/**
 * Format tool output for display
 */
export function formatToolOutput(toolName, output) {
  if (!output) return '<span class="text-gray-500 dark:text-gray-400">No output</span>';

  // Normalize tool name (remove mcp__sims__ prefix)
  const normalizedName = toolName.replace(/^mcp__sims__/, '');

  // Use specific formatter if available
  const formatter = ToolOutputFormatters[normalizedName];
  if (formatter) {
    return formatter(output);
  }

  // Parse if it's a string that looks like JSON
  let parsedOutput = output;
  if (typeof output === 'string') {
    try {
      parsedOutput = JSON.parse(output);
    } catch (e) {
      // Not JSON, use as-is
    }
  }

  // Extract text from array format
  if (Array.isArray(parsedOutput) && parsedOutput[0]?.type === 'text') {
    parsedOutput = parsedOutput[0].text;
  }

  // Default: pretty output
  if (typeof parsedOutput === 'string') {
    return `<pre class="font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap">${escapeHtml(parsedOutput)}</pre>`;
  }

  return `<pre class="font-mono text-gray-800 dark:text-gray-200">${escapeHtml(JSON.stringify(parsedOutput, null, 2))}</pre>`;
}
