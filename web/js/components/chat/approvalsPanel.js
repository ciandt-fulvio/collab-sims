/**
 * Approvals Panel Component
 * Handles approval requests and responses
 */

export function approvalsPanel() {
  return {
    // Data
    approvals: [],

    // Approval mode state
    approvalMode: 'auto',  // 'auto' | 'interactive' | 'manual'
    showApprovalModeDropdown: false,

    // Toggle approval mode dropdown
    toggleApprovalModeDropdown() {
      this.showApprovalModeDropdown = !this.showApprovalModeDropdown;
    },

    // Set approval mode
    async setApprovalMode(mode) {
      this.approvalMode = mode;
      this.showApprovalModeDropdown = false;

      // Update session config if session exists
      if (this.sessionId) {
        try {
          await this.api.updateApprovalConfig(this.sessionId, {
            mode: mode,
            tool_policies: {
              'Bash': 'high',
              'Write': 'medium',
              'Edit': 'medium',
              'Read': 'safe',
              'Glob': 'safe',
              'Grep': 'safe',
            },
            auto_approved_tools: []
          });
          console.log('✅ Approval mode updated to:', mode);
        } catch (error) {
          console.error('Failed to update approval mode:', error);
          alert('Failed to update approval mode. Check console for details.');
        }
      }
    },

    // Get approval mode label
    getApprovalModeLabel() {
      const labels = {
        'auto': 'Auto',
        'interactive': 'Interactive',
        'manual': 'Manual'
      };
      return labels[this.approvalMode] || 'Interactive';
    },

    // Get approval mode icon
    getApprovalModeIcon() {
      const icons = {
        auto: '🔓',
        interactive: '🔐',
        manual: '🔒'
      };
      return icons[this.approvalMode] || '🔐';
    },

    // Send approval response
    async sendApprovalResponse(approvalId, approved) {
      try {
        await this.api.sendApprovalResponse(this.sessionId, approvalId, approved);
      } catch (error) {
        console.error('Failed to send approval response:', error);
        alert('Failed to send approval response: ' + error.message);
      }
    },

    // Reset approvals state
    resetApprovals() {
      this.approvals = [];
    },
  };
}
