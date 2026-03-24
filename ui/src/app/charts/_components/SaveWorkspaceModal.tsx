'use client';

interface SaveWorkspaceModalProps {
  workspaceName: string;
  setWorkspaceName: (v: string) => void;
  onSave: (name: string) => void;
  onClose: () => void;
  activeWorkspaceId: string | null;
  formStyle: React.CSSProperties;
}

export default function SaveWorkspaceModal({
  workspaceName,
  setWorkspaceName,
  onSave,
  onClose,
  activeWorkspaceId,
  formStyle,
}: SaveWorkspaceModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 dark:bg-black/70" onClick={onClose}>
      <div className="bg-card border border-border/50 rounded-[var(--radius)] shadow-lg p-5 w-[340px]" onClick={(e) => e.stopPropagation()}>
        <h3 className="section-title mb-4">Save Workspace</h3>
        <input
          autoFocus
          type="text"
          value={workspaceName}
          onChange={(e) => setWorkspaceName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && workspaceName.trim()) onSave(workspaceName.trim()); }}
          placeholder="Workspace name..."
          className="w-full px-2.5 py-2 text-[12px] border border-border/50 rounded-[var(--radius)] bg-background text-foreground focus:outline-none focus:border-primary/50 focus:ring-2 focus:ring-primary/10 transition-colors"
          style={formStyle}
        />
        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 h-8 rounded-[var(--radius)] text-[11px] font-medium border border-border/40 text-muted-foreground hover:text-foreground hover:border-border/60 transition-colors">Cancel</button>
          <button
            onClick={() => workspaceName.trim() && onSave(workspaceName.trim())}
            disabled={!workspaceName.trim()}
            className="flex-1 h-8 rounded-[var(--radius)] text-[11px] font-medium bg-foreground text-background hover:opacity-90 transition-colors disabled:opacity-30"
          >
            {activeWorkspaceId ? 'Update' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
