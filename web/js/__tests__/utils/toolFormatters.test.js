import { describe, it, expect } from 'vitest';
import { formatToolInput, formatToolOutput } from '../../utils/toolFormatters.js';

describe('formatToolInput', () => {
  it('should return empty object placeholder for null input', () => {
    const result = formatToolInput('Bash', null);
    expect(result).toContain('{}');
  });

  it('should format Bash tool input with $ prompt', () => {
    const input = { command: 'echo hello' };
    const result = formatToolInput('Bash', input);
    expect(result).toContain('$');
    expect(result).toContain('echo hello');
  });

  it('should format mcp__sims__Bash tool input', () => {
    const input = { command: 'ls -la' };
    const result = formatToolInput('mcp__sims__Bash', input);
    expect(result).toContain('$');
    expect(result).toContain('ls -la');
  });

  it('should format Write tool input with file path and content', () => {
    const input = { file_path: '/test/file.txt', content: 'Hello\nWorld' };
    const result = formatToolInput('Write', input);
    expect(result).toContain('/test/file.txt');
    expect(result).toContain('2 lines');
    expect(result).toContain('Hello');
  });

  it('should format Read tool input with file path', () => {
    const input = { file_path: '/test/readme.md' };
    const result = formatToolInput('Read', input);
    expect(result).toContain('/test/readme.md');
  });

  it('should format Edit tool input with old and new strings', () => {
    const input = {
      file_path: '/test/config.js',
      old_string: 'old value',
      new_string: 'new value',
    };
    const result = formatToolInput('Edit', input);
    expect(result).toContain('/test/config.js');
  });

  it('should return JSON for unknown tools', () => {
    const input = { foo: 'bar' };
    const result = formatToolInput('UnknownTool', input);
    expect(result).toContain('foo');
    expect(result).toContain('bar');
  });
});

describe('formatToolOutput', () => {
  it('should format Bash tool output with stdout', () => {
    const output = { stdout: 'Hello World', stderr: '', exit_code: 0 };
    const result = formatToolOutput('Bash', output);
    expect(result).toContain('Hello World');
  });

  it('should format Bash tool output with stderr', () => {
    const output = { stdout: '', stderr: 'Error occurred', exit_code: 1 };
    const result = formatToolOutput('Bash', output);
    expect(result).toContain('Error occurred');
  });

  it('should show exit code for non-zero exits', () => {
    const output = { stdout: '', stderr: '', exit_code: 127 };
    const result = formatToolOutput('Bash', output);
    expect(result).toContain('127');
  });

  it('should format Write tool output', () => {
    const output = { success: true, path: '/test/file.txt' };
    const result = formatToolOutput('Write', output);
    expect(result).toContain('/test/file.txt');
  });

  it('should format Read tool output with content preview', () => {
    const output = { content: 'File content here...', path: '/test/readme.md' };
    const result = formatToolOutput('Read', output);
    expect(result).toContain('File content');
  });

  it('should format Edit tool output', () => {
    const output = { success: true };
    const result = formatToolOutput('Edit', output);
    expect(result).toContain('success');
  });

  it('should handle error outputs', () => {
    const output = { error: 'File not found' };
    const result = formatToolOutput('Read', output);
    expect(result).toContain('File not found');
  });

  it('should handle string outputs', () => {
    const result = formatToolOutput('SomeTool', 'Simple string output');
    expect(result).toContain('Simple string output');
  });

  it('should handle JSON object outputs', () => {
    const output = { result: 'success', value: 42 };
    const result = formatToolOutput('CustomTool', output);
    expect(result).toContain('result');
    expect(result).toContain('42');
  });
});
