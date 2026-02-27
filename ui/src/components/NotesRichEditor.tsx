'use client';

import {
  type ChangeEvent,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  memo,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Node, mergeAttributes } from '@tiptap/core';
import { Editor } from '@tiptap/core';
import {
  EditorContent,
  NodeViewWrapper,
  ReactNodeViewRenderer,
  type NodeViewProps,
  useEditor,
} from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import Placeholder from '@tiptap/extension-placeholder';
import { Table, TableRow, TableHeader, TableCell } from '@tiptap/extension-table';
import {
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Code2,
  Square,
  Table as TableIcon,
  Minus,
  Image as ImageIcon,
  BarChart2,
  Search,
  Clock,
  X,
  Bold,
  Italic,
  Link as LinkIcon,
  Type,
  Undo2,
  Redo2,
} from 'lucide-react';
import { applyChartTheme } from '@/lib/chartTheme';
import { apiFetch } from '@/lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type UploadResult = { url: string; filename?: string | null };
export type ChartItem = { id: string; name?: string | null; category?: string | null };

interface NotesRichEditorProps {
  value: string;
  onChange: (html: string) => void;
  disabled?: boolean;
  onImageUpload: (file: File) => Promise<UploadResult>;
  minHeightClassName?: string;
  chartLibrary?: ChartItem[];
  onFetchChartSnapshot?: (chartId: string) => Promise<{
    figure: any;
    name?: string | null;
    updated_at?: string | null;
  }>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const MAX_UPLOAD_EDGE = 2200;
const MAX_DIRECT_UPLOAD_BYTES = 1_800_000;
const MIN_IMAGE_PERCENT = 20;
const MAX_IMAGE_PERCENT = 100;

const SLASH_COMMANDS = [
  { id: 'paragraph',      label: 'Text',          description: 'Plain paragraph',        icon: Heading1,    keywords: ['text', 'paragraph', 'p'] },
  { id: 'heading1',       label: 'Heading 1',     description: 'Large section title',    icon: Heading1,    keywords: ['h1', 'heading'] },
  { id: 'heading2',       label: 'Heading 2',     description: 'Medium section title',   icon: Heading2,    keywords: ['h2', 'heading'] },
  { id: 'heading3',       label: 'Heading 3',     description: 'Small section title',    icon: Heading3,    keywords: ['h3', 'heading'] },
  { id: 'bulletList',     label: 'Bullet List',   description: 'Unordered list',         icon: List,        keywords: ['ul', 'bullet', 'list'] },
  { id: 'orderedList',    label: 'Numbered List', description: 'Ordered list',           icon: ListOrdered, keywords: ['ol', 'numbered', 'ordered'] },
  { id: 'codeBlock',      label: 'Code',          description: 'Code block',             icon: Code2,       keywords: ['code', 'pre', 'mono'] },
  { id: 'blockquote',     label: 'Quote',         description: 'Callout / quote block',  icon: Square,      keywords: ['quote', 'blockquote', 'callout', 'box'] },
  { id: 'table',          label: 'Table',         description: '3 × 3 table',            icon: TableIcon,   keywords: ['table', 'grid', 'data'] },
  { id: 'horizontalRule', label: 'Divider',       description: 'Horizontal rule',        icon: Minus,       keywords: ['divider', 'hr', 'rule', 'line'] },
  { id: 'image',          label: 'Image',         description: 'Upload an image',        icon: ImageIcon,   keywords: ['image', 'photo', 'img'] },
  { id: 'chart',          label: 'Chart',         description: 'Embed a chart snapshot', icon: BarChart2,   keywords: ['chart', 'graph', 'plot', 'visualization'] },
  { id: 'callout',        label: 'Callout',       description: 'Highlighted callout box', icon: Square,     keywords: ['callout', 'highlight', 'note', 'info', 'alert', 'box', 'tip'] },
] as const;

type SlashCommandId = (typeof SLASH_COMMANDS)[number]['id'];

// ─────────────────────────────────────────────────────────────────────────────
// Resizable image node
// ─────────────────────────────────────────────────────────────────────────────

function parseWidthPercent(width: unknown): number {
  if (typeof width === 'number' && Number.isFinite(width)) {
    return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round(width)));
  }
  if (typeof width !== 'string') return 100;
  const trimmed = width.trim().toLowerCase();
  if (!trimmed) return 100;
  if (trimmed.endsWith('%')) {
    const pct = Number(trimmed.replace('%', ''));
    if (Number.isFinite(pct)) {
      return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round(pct)));
    }
  }
  if (trimmed.endsWith('px')) {
    const px = Number(trimmed.replace('px', ''));
    if (Number.isFinite(px)) {
      return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round((px / 960) * 100)));
    }
  }
  const value = Number(trimmed);
  if (Number.isFinite(value)) {
    return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round(value)));
  }
  return 100;
}

function normalizeWidth(width: unknown): string {
  return `${parseWidthPercent(width)}%`;
}

function ResizableImageNode({ node, selected, updateAttributes, editor }: NodeViewProps) {
  const [isDragging, setIsDragging] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    return () => {
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
  }, []);

  const startResize = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      if (!editor.isEditable) return;
      event.preventDefault();
      event.stopPropagation();

      const editorRoot = editor.view.dom as HTMLElement;
      const containerWidth = Math.max(editorRoot?.clientWidth || 1, 1);
      const startX = event.clientX;
      const initialPercent = parseWidthPercent(node.attrs.width);
      const initialPx = (initialPercent / 100) * containerWidth;

      let rafId = 0;
      let pendingPercent = initialPercent;

      const flush = () => {
        rafId = 0;
        updateAttributes({ width: pendingPercent });
      };

      const onMove = (moveEvent: PointerEvent) => {
        const deltaX = moveEvent.clientX - startX;
        const nextPx = Math.max(
          containerWidth * (MIN_IMAGE_PERCENT / 100),
          Math.min(containerWidth, initialPx + deltaX)
        );
        pendingPercent = Math.max(
          MIN_IMAGE_PERCENT,
          Math.min(MAX_IMAGE_PERCENT, Math.round((nextPx / containerWidth) * 100))
        );
        if (!rafId) rafId = window.requestAnimationFrame(flush);
      };

      const stop = () => {
        if (rafId) { window.cancelAnimationFrame(rafId); rafId = 0; }
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', stop);
        document.removeEventListener('pointercancel', stop);
        cleanupRef.current = null;
        setIsDragging(false);
      };

      cleanupRef.current = stop;
      setIsDragging(true);
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', stop);
      document.addEventListener('pointercancel', stop);
    },
    [editor, node.attrs.width, updateAttributes]
  );

  const width = normalizeWidth(node.attrs.width);

  return (
    <NodeViewWrapper
      as="span"
      data-note-image-node
      className={`notes-image-node ${selected ? 'is-selected' : ''} ${isDragging ? 'is-dragging' : ''}`}
      style={{ width }}
    >
      <img
        src={node.attrs.src}
        alt={node.attrs.alt || ''}
        title={node.attrs.title || ''}
        draggable={false}
      />
      {editor.isEditable && (
        <button
          type="button"
          className="notes-image-handle"
          onPointerDown={startResize}
          title="Drag to resize image"
          aria-label="Drag to resize image"
        />
      )}
    </NodeViewWrapper>
  );
}

const RichImage = Image.extend({
  addAttributes() {
    const parentAttributes = this.parent?.() || {};
    return {
      ...parentAttributes,
      width: {
        default: 100,
        parseHTML: (element) =>
          parseWidthPercent(
            element.getAttribute('data-width') ||
              element.style.width ||
              (element.getAttribute('width') ? `${element.getAttribute('width')}px` : '100%')
          ),
        renderHTML: (attributes) => {
          const width = normalizeWidth(attributes.width);
          return { 'data-width': width, style: `width:${width};height:auto;` };
        },
      },
    };
  },
  addNodeView() {
    return ReactNodeViewRenderer(ResizableImageNode);
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Chart block — renders a point-in-time Plotly snapshot
// ─────────────────────────────────────────────────────────────────────────────

// Read theme from the <html> class since NodeViews render in a separate React subtree
// and don't have access to ThemeContext.
function useDocTheme(): 'light' | 'dark' {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof document === 'undefined') return 'dark';
    return document.documentElement.classList.contains('light') ? 'light' : 'dark';
  });
  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => {
      setTheme(root.classList.contains('light') ? 'light' : 'dark');
    });
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  return theme;
}

function ChartBlockNodeView({ node, selected, deleteNode, updateAttributes, editor }: NodeViewProps) {
  const theme = useDocTheme();
  const chartId = node.attrs.chartId as string;
  const chartName = node.attrs.chartName as string | null;
  const figureJson = node.attrs.figureJson as string | null;
  const snapshotAt = node.attrs.snapshotAt as string | null;
  const chartHeight = (node.attrs.chartHeight as number) || 320;
  const plotRef = useRef<HTMLDivElement>(null);
  const resizeCleanupRef = useRef<(() => void) | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);

  const loadSnapshot = useCallback(async () => {
    if (!chartId) return;
    setSnapshotLoading(true);
    setSnapshotError(null);
    try {
      // 1. Try the dedicated dashboard figure endpoint
      const res1 = await apiFetch(`/api/v1/dashboard/charts/${chartId}/figure`);
      if (res1.ok) {
        const figure = await res1.json();
        if (figure && typeof figure === 'object') {
          updateAttributes({ figureJson: JSON.stringify(figure), snapshotAt: new Date().toISOString() });
          return;
        }
      }
      // 2. Try full chart record
      const res2 = await apiFetch(`/api/custom/${chartId}`);
      if (res2.ok) {
        const data = await res2.json();
        if (data?.figure) {
          updateAttributes({ figureJson: JSON.stringify(data.figure), snapshotAt: new Date().toISOString() });
          return;
        }
      }
      // 3. No stored figure — re-execute the chart code server-side
      const res3 = await apiFetch(`/api/custom/${chartId}/refresh`, { method: 'POST' });
      if (res3.ok) {
        const data = await res3.json();
        if (data?.figure) {
          updateAttributes({ figureJson: JSON.stringify(data.figure), snapshotAt: new Date().toISOString() });
          return;
        }
      }
      setSnapshotError('No figure — open chart in Studio, run the code, then retry.');
    } catch (err) {
      setSnapshotError(`Failed to load: ${err instanceof Error ? err.message : 'unknown error'}`);
    } finally {
      setSnapshotLoading(false);
    }
  }, [chartId, updateAttributes]);

  useEffect(() => {
    return () => {
      resizeCleanupRef.current?.();
      resizeCleanupRef.current = null;
    };
  }, []);

  // Render/update the Plotly snapshot whenever figure data, height, or theme changes
  useEffect(() => {
    if (!figureJson || !plotRef.current) return;
    let cancelled = false;
    let figure: any;
    try { figure = JSON.parse(figureJson); } catch { return; }

    // Apply dark/light theme to the stored snapshot.
    // applyChartTheme sets autosize:true and clears width/height.
    // The container div has explicit width:100% and height:chartHeight,
    // so Plotly will autosize to fill the container exactly.
    const themed = applyChartTheme(figure, theme);

    (async () => {
      const Plotly = (await import('plotly.js-dist-min')) as any;
      if (cancelled || !plotRef.current) return;
      try { Plotly.purge(plotRef.current); } catch { /* ok */ }
      Plotly.react(
        plotRef.current,
        themed.data || [],
        themed.layout,
        { responsive: true, displayModeBar: false }
      );
    })();

    return () => { cancelled = true; };
  }, [figureJson, chartHeight, theme]);

  // Purge Plotly on unmount
  useEffect(() => {
    return () => {
      const el = plotRef.current;
      if (el) {
        import('plotly.js-dist-min').then((Plotly: any) => {
          try { Plotly.purge(el); } catch { /* ok */ }
        });
      }
    };
  }, []);

  const startHeightResize = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!editor.isEditable) return;
      event.preventDefault();
      event.stopPropagation();

      const startY = event.clientY;
      const initialHeight = chartHeight;
      let rafId = 0;
      let pendingHeight = initialHeight;

      const flush = () => {
        rafId = 0;
        updateAttributes({ chartHeight: pendingHeight });
      };

      const onMove = (e: PointerEvent) => {
        pendingHeight = Math.max(180, Math.min(900, initialHeight + (e.clientY - startY)));
        if (!rafId) rafId = window.requestAnimationFrame(flush);
      };

      const stop = () => {
        if (rafId) { window.cancelAnimationFrame(rafId); rafId = 0; }
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', stop);
        document.removeEventListener('pointercancel', stop);
        resizeCleanupRef.current = null;
      };

      resizeCleanupRef.current = stop;
      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', stop);
      document.addEventListener('pointercancel', stop);
    },
    [editor.isEditable, chartHeight, updateAttributes]
  );

  const formattedDate = snapshotAt
    ? new Date(snapshotAt).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  return (
    <NodeViewWrapper contentEditable={false}>
      <div className={`notes-chart-node ${selected ? 'is-selected' : ''}`}>
        <div className="notes-chart-toolbar">
          <div className="flex items-center gap-2 ml-auto">
            {editor.isEditable && (
              <button
                type="button"
                className="notes-chart-remove"
                onClick={deleteNode}
                title="Remove chart"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {figureJson ? (
          <div ref={plotRef} style={{ width: '100%', height: chartHeight }} />
        ) : (
          <div className="notes-chart-empty flex flex-col items-center gap-2">
            <span className="text-[11px] text-muted-foreground/50">
              {snapshotError ?? 'No snapshot data.'}
            </span>
            {editor.isEditable && (
              <button
                type="button"
                disabled={snapshotLoading}
                onClick={loadSnapshot}
                className="px-2.5 py-1 text-[10px] rounded border border-border/50 text-muted-foreground hover:text-foreground hover:border-border transition-colors disabled:opacity-40"
              >
                {snapshotLoading ? 'Loading…' : 'Load snapshot'}
              </button>
            )}
          </div>
        )}
        {formattedDate && (
          <div className="notes-chart-timestamp mt-2">
            <Clock className="w-3 h-3 inline-block mr-1 opacity-50" />
            {formattedDate}
          </div>
        )}

        {editor.isEditable && (
          <div
            className="notes-chart-resize-handle"
            onPointerDown={startHeightResize}
            title="Drag to resize"
          />
        )}
      </div>
    </NodeViewWrapper>
  );
}

const ChartBlock = Node.create({
  name: 'chartBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      chartId: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-chart-id'),
        renderHTML: (attrs) => ({ 'data-chart-id': attrs.chartId || '' }),
      },
      chartName: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-chart-name'),
        renderHTML: (attrs) => ({ 'data-chart-name': attrs.chartName || '' }),
      },
      // Full Plotly figure JSON — stored for point-in-time rendering
      figureJson: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-figure') || null,
        renderHTML: (attrs) => (attrs.figureJson ? { 'data-figure': attrs.figureJson } : {}),
      },
      // ISO timestamp of when the snapshot was captured
      snapshotAt: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-snapshot-at') || null,
        renderHTML: (attrs) => (attrs.snapshotAt ? { 'data-snapshot-at': attrs.snapshotAt } : {}),
      },
      // User-adjustable chart height in pixels
      chartHeight: {
        default: 320,
        parseHTML: (el) => {
          const v = el.getAttribute('data-chart-height');
          return v ? Math.max(180, Math.min(900, Number(v))) : 320;
        },
        renderHTML: (attrs) => ({ 'data-chart-height': String(attrs.chartHeight || 320) }),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'div[data-chart-block]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-chart-block': 'true' }, HTMLAttributes)];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ChartBlockNodeView);
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Formatting toolbar
// ─────────────────────────────────────────────────────────────────────────────

function FormattingToolbar({ editor, onSetLink }: { editor: Editor; onSetLink: () => void }) {
  const base = 'transition-colors flex items-center justify-center rounded disabled:opacity-30';
  const iconBtn = (active: boolean) =>
    `${base} h-6 w-6 ${active ? 'bg-sky-500/[0.14] text-foreground' : 'text-muted-foreground/50 hover:text-foreground hover:bg-foreground/[0.07]'}`;
  const labelBtn = (active: boolean) =>
    `${base} h-6 px-1.5 text-[11px] font-semibold ${active ? 'bg-sky-500/[0.14] text-foreground' : 'text-muted-foreground/50 hover:text-foreground hover:bg-foreground/[0.07]'}`;
  const sep = <div className="w-px h-3.5 bg-border/30 mx-0.5 shrink-0" />;

  // Track active state for paragraph (not inside list/quote)
  const isPlainPara = editor.isActive('paragraph') && !editor.isActive('blockquote');

  return (
    <div
      className="flex items-center gap-0.5 px-1 pt-1 pb-1.5 flex-wrap border-b border-border/20"
      onMouseDown={(e) => e.preventDefault()}
    >
      {/* Block type */}
      <button type="button" onMouseDown={() => editor.chain().focus().setParagraph().run()} className={labelBtn(isPlainPara)} title="Text">
        <Type className="w-3 h-3" />
      </button>
      <button type="button" onMouseDown={() => editor.chain().focus().setHeading({ level: 1 }).run()} className={labelBtn(editor.isActive('heading', { level: 1 }))} title="Heading 1">H1</button>
      <button type="button" onMouseDown={() => editor.chain().focus().setHeading({ level: 2 }).run()} className={labelBtn(editor.isActive('heading', { level: 2 }))} title="Heading 2">H2</button>
      <button type="button" onMouseDown={() => editor.chain().focus().setHeading({ level: 3 }).run()} className={labelBtn(editor.isActive('heading', { level: 3 }))} title="Heading 3">H3</button>

      {sep}

      {/* Text marks */}
      <button type="button" onMouseDown={() => editor.chain().focus().toggleBold().run()} className={iconBtn(editor.isActive('bold'))} title="Bold (⌘B)">
        <Bold className="w-3.5 h-3.5" />
      </button>
      <button type="button" onMouseDown={() => editor.chain().focus().toggleItalic().run()} className={iconBtn(editor.isActive('italic'))} title="Italic (⌘I)">
        <Italic className="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        onMouseDown={() => editor.chain().focus().toggleStrike().run()}
        className={`${base} h-6 w-6 text-[12px] font-semibold line-through ${editor.isActive('strike') ? 'bg-sky-500/[0.14] text-foreground' : 'text-muted-foreground/50 hover:text-foreground hover:bg-foreground/[0.07]'}`}
        title="Strikethrough"
      >S</button>
      <button type="button" onMouseDown={() => editor.chain().focus().toggleCode().run()} className={iconBtn(editor.isActive('code'))} title="Inline code">
        <Code2 className="w-3 h-3" />
      </button>
      <button type="button" onMouseDown={onSetLink} className={iconBtn(editor.isActive('link'))} title="Link">
        <LinkIcon className="w-3 h-3" />
      </button>

      {sep}

      {/* Lists & blocks */}
      <button type="button" onMouseDown={() => editor.chain().focus().toggleBulletList().run()} className={iconBtn(editor.isActive('bulletList'))} title="Bullet list">
        <List className="w-3.5 h-3.5" />
      </button>
      <button type="button" onMouseDown={() => editor.chain().focus().toggleOrderedList().run()} className={iconBtn(editor.isActive('orderedList'))} title="Numbered list">
        <ListOrdered className="w-3.5 h-3.5" />
      </button>
      <button type="button" onMouseDown={() => editor.chain().focus().toggleBlockquote().run()} className={iconBtn(editor.isActive('blockquote'))} title="Callout / Quote">
        <Square className="w-3 h-3" />
      </button>

      {sep}

      {/* History */}
      <button type="button" onMouseDown={() => editor.chain().focus().undo().run()} className={iconBtn(false)} title="Undo (⌘Z)">
        <Undo2 className="w-3.5 h-3.5" />
      </button>
      <button type="button" onMouseDown={() => editor.chain().focus().redo().run()} className={iconBtn(false)} title="Redo (⌘⇧Z)">
        <Redo2 className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Slash command palette
// ─────────────────────────────────────────────────────────────────────────────

function SlashCommandMenu({
  query,
  top,
  left,
  onSelect,
  onClose,
}: {
  query: string;
  top: number;
  left: number;
  onSelect: (id: SlashCommandId) => void;
  onClose: () => void;
}) {
  const [index, setIndex] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const activeItemRef = useRef<HTMLButtonElement>(null);
  const [posStyle, setPosStyle] = useState<CSSProperties>({
    position: 'fixed', top, left, zIndex: 9999, opacity: 0,
  });

  const filtered = useMemo(() => SLASH_COMMANDS.filter((cmd) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return cmd.label.toLowerCase().includes(q) || cmd.keywords.some((k) => k.includes(q));
  }), [query]);

  useEffect(() => { setIndex(0); }, [query]);

  // Scroll active item into view
  useEffect(() => {
    activeItemRef.current?.scrollIntoView({ block: 'nearest' });
  }, [index]);

  // Reposition to avoid viewport overflow (bottom flip + right clamp)
  useLayoutEffect(() => {
    if (!menuRef.current) return;
    const rect = menuRef.current.getBoundingClientRect();
    const overflowsBottom = rect.bottom > window.innerHeight - 8;
    const clampedLeft = Math.max(8, Math.min(left, window.innerWidth - rect.width - 8));
    setPosStyle({
      position: 'fixed',
      top: overflowsBottom ? undefined : top,
      bottom: overflowsBottom ? window.innerHeight - top : undefined,
      left: clampedLeft,
      zIndex: 9999,
      opacity: 1,
    });
  }, [top, left]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault(); e.stopPropagation();
        setIndex((i) => (i + 1) % Math.max(1, filtered.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault(); e.stopPropagation();
        setIndex((i) => (i - 1 + Math.max(1, filtered.length)) % Math.max(1, filtered.length));
      } else if (e.key === 'Enter' && filtered.length > 0) {
        e.preventDefault(); e.stopPropagation();
        const cmd = filtered[index];
        if (cmd) onSelect(cmd.id as SlashCommandId);
      } else if (e.key === 'Escape') {
        e.preventDefault(); e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener('keydown', handler, { capture: true });
    return () => window.removeEventListener('keydown', handler, { capture: true });
  }, [filtered, index, onSelect, onClose]);

  if (!filtered.length) return null;

  return (
    <div
      ref={menuRef}
      style={posStyle}
      className="w-44 rounded-lg border border-border/60 bg-background shadow-lg shadow-black/20 overflow-hidden"
    >
      <div className="px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-muted-foreground/40">
        Blocks
      </div>
      <div className="max-h-48 overflow-y-auto pb-0.5">
        {filtered.map((cmd, i) => {
          const Icon = cmd.icon;
          return (
            <button
              key={cmd.id}
              ref={i === index ? activeItemRef : undefined}
              type="button"
              onMouseEnter={() => setIndex(i)}
              onMouseDown={(e) => { e.preventDefault(); onSelect(cmd.id as SlashCommandId); }}
              className={`w-full px-2 py-0.5 flex items-center gap-1.5 text-left transition-colors ${
                i === index
                  ? 'bg-sky-500/10 text-foreground'
                  : 'text-muted-foreground hover:bg-accent/10 hover:text-foreground'
              }`}
            >
              <div className="w-5 h-5 rounded border border-border/40 bg-card/60 flex items-center justify-center shrink-0">
                <Icon className="w-2.5 h-2.5" />
              </div>
              <div className="min-w-0">
                <div className="text-[10px] font-medium leading-tight truncate">{cmd.label}</div>
                <div className="text-[9px] text-muted-foreground/50 leading-tight truncate">{cmd.description}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Chart picker (shown after /chart command)
// ─────────────────────────────────────────────────────────────────────────────

function ChartPickerMenu({
  chartLibrary,
  top,
  left,
  onSelect,
  onClose,
}: {
  chartLibrary: ChartItem[];
  top: number;
  left: number;
  onSelect: (chart: ChartItem) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const activeItemRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [posStyle, setPosStyle] = useState<CSSProperties>({
    position: 'fixed', top, left, zIndex: 9999, opacity: 0,
  });

  // Reposition to avoid viewport overflow (bottom flip + right clamp)
  useLayoutEffect(() => {
    if (!menuRef.current) return;
    const rect = menuRef.current.getBoundingClientRect();
    const overflowsBottom = rect.bottom > window.innerHeight - 8;
    const clampedLeft = Math.max(8, Math.min(left, window.innerWidth - rect.width - 8));
    setPosStyle({
      position: 'fixed',
      top: overflowsBottom ? undefined : top,
      bottom: overflowsBottom ? window.innerHeight - top : undefined,
      left: clampedLeft,
      zIndex: 9999,
      opacity: 1,
    });
  }, [top, left]);

  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 30); }, []);

  const filtered = chartLibrary.filter((c) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (c.name || '').toLowerCase().includes(q) || (c.category || '').toLowerCase().includes(q);
  }).slice(0, 40);

  // Reset active index when filter changes
  useEffect(() => { setActiveIndex(0); }, [query]);

  // Scroll active item into view
  useEffect(() => {
    activeItemRef.current?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); onClose(); return; }
      if (e.key === 'ArrowDown') {
        e.preventDefault(); e.stopPropagation();
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault(); e.stopPropagation();
        setActiveIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === 'Enter' && filtered.length > 0) {
        e.preventDefault(); e.stopPropagation();
        onSelect(filtered[activeIndex]);
        return;
      }
    };
    window.addEventListener('keydown', handler, { capture: true });
    return () => window.removeEventListener('keydown', handler, { capture: true });
  }, [onClose, onSelect, filtered, activeIndex]);

  return (
    <div
      ref={menuRef}
      style={posStyle}
      className="w-52 rounded-md border border-border/60 bg-background shadow-lg shadow-black/20 overflow-hidden"
    >
      <div className="px-1.5 pt-1.5 pb-1 border-b border-border/40">
        <div className="relative">
          <Search className="w-2.5 h-2.5 absolute left-1.5 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search..."
            className="w-full h-5 pl-5 pr-1.5 rounded border border-border/50 bg-background/60 text-[10px] outline-none focus:ring-1 focus:ring-sky-500/30 placeholder:text-muted-foreground/35"
          />
        </div>
      </div>
      <div ref={listRef} className="max-h-40 overflow-y-auto py-0.5">
        {filtered.length === 0 && (
          <div className="px-2 py-1.5 text-[10px] text-muted-foreground/50">No charts found.</div>
        )}
        {filtered.map((chart, i) => (
          <button
            key={chart.id}
            ref={i === activeIndex ? activeItemRef : undefined}
            type="button"
            onMouseEnter={() => setActiveIndex(i)}
            onMouseDown={(e) => { e.preventDefault(); onSelect(chart); }}
            className={`w-full px-2 py-0.5 flex items-center gap-1.5 text-left transition-colors ${i === activeIndex ? 'bg-accent/15' : ''}`}
          >
            <BarChart2 className="w-2.5 h-2.5 text-sky-400 shrink-0" />
            <div className="min-w-0 flex-1">
              <span className="text-[10px] font-medium text-foreground truncate block leading-snug">{chart.name || chart.id}</span>
              {chart.category && (
                <span className="text-[9px] text-muted-foreground/50 truncate block leading-none">{chart.category}</span>
              )}
            </div>
          </button>
        ))}
      </div>
      {filtered.length > 0 && (
        <div className="px-2 py-0.5 border-t border-border/30">
          <span className="text-[8px] text-muted-foreground/35 font-mono">↑↓ · ↵ select · esc</span>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Image compression
// ─────────────────────────────────────────────────────────────────────────────

async function compressImageForUpload(file: File): Promise<File> {
  if (typeof window === 'undefined') return file;
  if (!file.type.startsWith('image/')) return file;
  if (file.size <= MAX_DIRECT_UPLOAD_BYTES) return file;
  if (typeof createImageBitmap !== 'function') return file;

  try {
    const bitmap = await createImageBitmap(file);
    const largestEdge = Math.max(bitmap.width, bitmap.height);
    const scale = largestEdge > MAX_UPLOAD_EDGE ? MAX_UPLOAD_EDGE / largestEdge : 1;
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    const ctx = canvas.getContext('2d');
    if (!ctx) { bitmap.close(); return file; }
    ctx.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();

    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, 'image/webp', 0.82);
    });
    if (!blob || blob.size >= file.size) return file;

    const baseName = (file.name || 'image').replace(/\.[^/.]+$/, '');
    return new File([blob], `${baseName || 'image'}.webp`, { type: 'image/webp' });
  } catch {
    return file;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main editor
// ─────────────────────────────────────────────────────────────────────────────

function NotesRichEditor({
  value,
  onChange,
  disabled = false,
  onImageUpload,
  minHeightClassName = 'min-h-[48vh]',
  chartLibrary = [],
  onFetchChartSnapshot,
}: NotesRichEditorProps) {
  const editorRef = useRef<Editor | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const slashStartPosRef = useRef<number | null>(null);
  const onFetchChartSnapshotRef = useRef(onFetchChartSnapshot);
  useEffect(() => { onFetchChartSnapshotRef.current = onFetchChartSnapshot; }, [onFetchChartSnapshot]);

  const [slashMenu, setSlashMenu] = useState<{ query: string; top: number; left: number } | null>(null);
  const [chartPicker, setChartPicker] = useState<{ top: number; left: number } | null>(null);
  const [bubbleMenu, setBubbleMenu] = useState<{ top: number; left: number } | null>(null);

  const uploadAndInsertImages = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        const optimized = await compressImageForUpload(file);
        const image = await onImageUpload(optimized);
        const activeEditor = editorRef.current;
        if (!activeEditor) return;
        activeEditor
          .chain()
          .focus()
          .setImage({ src: image.url, alt: image.filename || file.name || 'image', width: 100 })
          .run();
      }
    },
    [onImageUpload]
  );

  // Fetch the chart's current figure JSON and insert as a static snapshot block
  const insertChartBlock = useCallback(async (chart: ChartItem) => {
    const ed = editorRef.current;
    if (!ed) return;

    // Capture positions before async op
    const { from } = ed.state.selection;
    const startPos = slashStartPosRef.current;
    slashStartPosRef.current = null;
    setSlashMenu(null);
    setChartPicker(null);

    // Fetch point-in-time snapshot
    let figureJson: string | null = null;
    const snapshotAt = new Date().toISOString();
    if (onFetchChartSnapshotRef.current) {
      try {
        const snapshot = await onFetchChartSnapshotRef.current(chart.id);
        if (snapshot?.figure) figureJson = JSON.stringify(snapshot.figure);
      } catch { /* insert without figure if fetch fails */ }
    }

    const attrs = {
      chartId: chart.id,
      chartName: chart.name || null,
      figureJson,
      snapshotAt,
      chartHeight: 320,
    };

    const activeEd = editorRef.current;
    if (!activeEd) return;

    if (startPos !== null) {
      try {
        activeEd.chain().focus()
          .deleteRange({ from: startPos, to: from })
          .insertContent({ type: 'chartBlock', attrs })
          .run();
      } catch {
        activeEd.chain().focus().insertContent({ type: 'chartBlock', attrs }).run();
      }
    } else {
      activeEd.chain().focus().insertContent({ type: 'chartBlock', attrs }).run();
    }
  }, []);

  const executeSlashCommand = useCallback((id: SlashCommandId) => {
    const ed = editorRef.current;
    if (!ed) return;

    setSlashMenu(null);

    if (id === 'chart') {
      const coords = ed.view.coordsAtPos(ed.state.selection.from);
      setChartPicker({ top: coords.bottom, left: coords.left });
      return; // slash text deleted when chart is selected
    }

    if (slashStartPosRef.current !== null) {
      const { from } = ed.state.selection;
      ed.chain().focus().deleteRange({ from: slashStartPosRef.current, to: from }).run();
      slashStartPosRef.current = null;
    }

    switch (id) {
      case 'paragraph':      ed.chain().focus().setParagraph().run(); break;
      case 'heading1':       ed.chain().focus().setHeading({ level: 1 }).run(); break;
      case 'heading2':       ed.chain().focus().setHeading({ level: 2 }).run(); break;
      case 'heading3':       ed.chain().focus().setHeading({ level: 3 }).run(); break;
      case 'bulletList':     ed.chain().focus().toggleBulletList().run(); break;
      case 'orderedList':    ed.chain().focus().toggleOrderedList().run(); break;
      case 'codeBlock':      ed.chain().focus().toggleCodeBlock().run(); break;
      case 'blockquote':     ed.chain().focus().insertContent('<blockquote><p></p></blockquote><p></p>').run(); break;
      case 'table':          ed.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(); break;
      case 'horizontalRule': ed.chain().focus().setHorizontalRule().run(); break;
      case 'image':          fileInputRef.current?.click(); break;
      case 'callout':        ed.chain().focus().insertContent('<blockquote><p>💡 </p></blockquote><p></p>').run(); break;
    }
  }, []);

  const setLink = useCallback(() => {
    const ed = editorRef.current;
    if (!ed || disabled) return;
    const previousUrl = ed.getAttributes('link').href || '';
    const url = window.prompt('Enter URL', previousUrl);
    if (url === null) return;
    if (url === '') { ed.chain().focus().unsetLink().run(); return; }
    const href = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    ed.chain().focus().extendMarkRange('link').setLink({ href }).run();
  }, [disabled]);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
      RichImage.configure({ allowBase64: false }),
      ChartBlock,
      Placeholder.configure({
        placeholder: "Write here… type '/' for blocks, '/chart' to embed a chart snapshot.",
      }),
    ],
    content: value || '',
    editable: !disabled,
    onCreate: ({ editor }) => { editorRef.current = editor; },
    onDestroy: () => { editorRef.current = null; },
    onSelectionUpdate: ({ editor }) => {
      const { selection } = editor.state;
      if (selection.empty || disabled) { setBubbleMenu(null); return; }
      try {
        const from = selection.from;
        const to = selection.to;
        const startCoords = editor.view.coordsAtPos(from);
        const endCoords = editor.view.coordsAtPos(to);
        setBubbleMenu({
          top: startCoords.top - 44,
          left: (startCoords.left + endCoords.left) / 2,
        });
      } catch { setBubbleMenu(null); }
    },
    onBlur: () => { setTimeout(() => setBubbleMenu(null), 150); },
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());

      if (disabled) return;
      const { state } = editor;
      const { selection } = state;
      const { $from } = selection;

      if ($from.parent.type.name !== 'paragraph') {
        setSlashMenu(null);
        slashStartPosRef.current = null;
        return;
      }

      const textBefore = $from.parent.textContent.slice(0, $from.parentOffset);
      if (textBefore.startsWith('/') && !textBefore.includes(' ')) {
        const query = textBefore.slice(1).toLowerCase();
        const coords = editor.view.coordsAtPos(selection.from);
        if (slashStartPosRef.current === null) {
          slashStartPosRef.current = selection.from - textBefore.length;
        }
        setSlashMenu({ query, top: coords.bottom, left: coords.left });
      } else {
        setSlashMenu(null);
        slashStartPosRef.current = null;
      }
    },
    editorProps: {
      attributes: {
        class: `notes-editor-content px-0 py-1 focus:outline-none ${minHeightClassName}`,
      },
      handlePaste: (_view, event) => {
        if (disabled) return false;
        const items = Array.from(event.clipboardData?.items || []);
        const files = items
          .filter((item) => item.type.startsWith('image/'))
          .map((item) => item.getAsFile())
          .filter((file): file is File => !!file);
        if (!files.length) return false;
        event.preventDefault();
        void uploadAndInsertImages(files);
        return true;
      },
      handleDrop: (_view, event, _slice, moved) => {
        if (disabled || moved) return false;
        const files = Array.from(event.dataTransfer?.files || []).filter((file) =>
          file.type.startsWith('image/')
        );
        if (!files.length) return false;
        event.preventDefault();
        void uploadAndInsertImages(files);
        return true;
      },
    },
  });

  useEffect(() => {
    if (!editor) return;
    const current = editor.getHTML();
    if ((value || '') !== current) {
      editor.commands.setContent(value || '', { emitUpdate: false });
    }
  }, [editor, value]);

  useEffect(() => {
    if (!editor) return;
    editor.setEditable(!disabled);
  }, [editor, disabled]);

  if (!editor) return null;

  return (
    <div>
      {/* Bubble menu — appears on text selection (Notion-style) */}
      {bubbleMenu && !disabled && (
        <div
          style={{
            position: 'fixed',
            top: bubbleMenu.top,
            left: bubbleMenu.left,
            transform: 'translateX(-50%)',
            zIndex: 9998,
          }}
          onMouseDown={(e) => e.preventDefault()}
          className="flex items-center gap-0.5 rounded-lg border border-border/60 bg-background shadow-xl shadow-black/20 p-1"
        >
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleBold().run()}
            className={`h-6 w-6 rounded flex items-center justify-center transition-colors ${
              editor.isActive('bold') ? 'bg-sky-500/20 text-sky-300' : 'text-muted-foreground hover:text-foreground hover:bg-accent/10'
            }`}
            title="Bold"
          >
            <Bold className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            className={`h-6 w-6 rounded flex items-center justify-center transition-colors ${
              editor.isActive('italic') ? 'bg-sky-500/20 text-sky-300' : 'text-muted-foreground hover:text-foreground hover:bg-accent/10'
            }`}
            title="Italic"
          >
            <Italic className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleStrike().run()}
            className={`h-6 w-6 rounded flex items-center justify-center text-[13px] line-through transition-colors ${
              editor.isActive('strike') ? 'bg-sky-500/20 text-sky-300' : 'text-muted-foreground hover:text-foreground hover:bg-accent/10'
            }`}
            title="Strikethrough"
          >
            S
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleCode().run()}
            className={`h-6 w-6 rounded flex items-center justify-center transition-colors ${
              editor.isActive('code') ? 'bg-sky-500/20 text-sky-300' : 'text-muted-foreground hover:text-foreground hover:bg-accent/10'
            }`}
            title="Inline Code"
          >
            <Code2 className="w-3 h-3" />
          </button>
          <div className="w-px h-4 bg-border/50 mx-0.5" />
          <button
            type="button"
            onClick={setLink}
            className={`h-6 w-6 rounded flex items-center justify-center transition-colors ${
              editor.isActive('link') ? 'bg-sky-500/20 text-sky-300' : 'text-muted-foreground hover:text-foreground hover:bg-accent/10'
            }`}
            title="Link"
          >
            <LinkIcon className="w-3 h-3" />
          </button>
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={async (event: ChangeEvent<HTMLInputElement>) => {
          const file = event.target.files?.[0];
          event.target.value = '';
          if (!file || !editor || disabled) return;
          try { await uploadAndInsertImages([file]); } catch { /* parent manages error state */ }
        }}
      />

      <div className="notes-editor">
        {!disabled && <FormattingToolbar editor={editor} onSetLink={setLink} />}
        <EditorContent editor={editor} />
      </div>

      {/* Slash command palette */}
      {slashMenu && !disabled && (
        <SlashCommandMenu
          query={slashMenu.query}
          top={slashMenu.top}
          left={slashMenu.left}
          onSelect={executeSlashCommand}
          onClose={() => {
            setSlashMenu(null);
            slashStartPosRef.current = null;
          }}
        />
      )}

      {/* Chart picker (triggered by /chart) */}
      {chartPicker && !disabled && (
        <ChartPickerMenu
          chartLibrary={chartLibrary}
          top={chartPicker.top}
          left={chartPicker.left}
          onSelect={insertChartBlock}
          onClose={() => {
            setChartPicker(null);
            slashStartPosRef.current = null;
            editorRef.current?.commands.focus();
          }}
        />
      )}
    </div>
  );
}

export default memo(NotesRichEditor);
