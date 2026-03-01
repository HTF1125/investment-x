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
import { Node, Extension, mergeAttributes } from '@tiptap/core';
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
import FontFamily from '@tiptap/extension-font-family';
import { TextStyle } from '@tiptap/extension-text-style';
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
  Loader2,
  X,
  Bold,
  Italic,
  Link as LinkIcon,
  ExternalLink,
  Play,
  Type,
  Columns2,
  Plus,
  Rows2,
  Trash2,
  GripVertical,
  ChevronDown,
  Check
} from 'lucide-react';
import { NodeSelection, Plugin, PluginKey } from '@tiptap/pm/state';
import { applyChartTheme } from '@/lib/chartTheme';
import { apiFetch, apiFetchJson } from '@/lib/api';

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type UploadResult = { url: string; filename?: string | null };
export type ChartItem = { id: string; name?: string | null; category?: string | null };
type LinkPreviewData = {
  url: string;
  kind?: string;
  provider?: string | null;
  title?: string | null;
  subtitle?: string | null;
  description?: string | null;
  image_url?: string | null;
};

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
  { id: 'paragraph',      label: 'Text',          description: 'Just start writing with plain text.', icon: Type,    keywords: ['text', 'paragraph', 'p'] },
  { id: 'heading1',       label: 'Heading 1',     description: 'Big section heading.',    icon: Heading1,    keywords: ['h1', 'heading'] },
  { id: 'heading2',       label: 'Heading 2',     description: 'Medium section heading.', icon: Heading2,    keywords: ['h2', 'heading'] },
  { id: 'heading3',       label: 'Heading 3',     description: 'Small section heading.',  icon: Heading3,    keywords: ['h3', 'heading'] },
  { id: 'table',          label: 'Table',         description: 'Add simple tabular content.', icon: TableIcon,   keywords: ['table', 'grid', 'data'] },
  { id: 'bulletList',     label: 'Bulleted list', description: 'Create a simple bulleted list.', icon: List,        keywords: ['ul', 'bullet', 'list'] },
  { id: 'orderedList',    label: 'Numbered list', description: 'Create a list with numbering.',  icon: ListOrdered, keywords: ['ol', 'numbered', 'ordered'] },
  { id: 'blockquote',     label: 'Quote',         description: 'Capture a quote.',        icon: Square,      keywords: ['quote', 'blockquote'] },
  { id: 'horizontalRule', label: 'Divider',       description: 'Visually divide blocks.', icon: Minus,       keywords: ['divider', 'hr', 'rule', 'line'] },
  { id: 'codeBlock',      label: 'Code',          description: 'Capture a code snippet.', icon: Code2,       keywords: ['code', 'pre', 'mono'] },
  { id: 'image',          label: 'Image',         description: 'Upload or embed with a link.', icon: ImageIcon,   keywords: ['image', 'photo', 'img'] },
  { id: 'chart',          label: 'Chart',         description: 'Embed an interactive chart snapshot.', icon: BarChart2,   keywords: ['chart', 'graph', 'plot', 'visualization'] },
  { id: 'callout',        label: 'Callout',       description: 'Make writing stand out.', icon: Square,     keywords: ['callout', 'highlight', 'note', 'info', 'alert', 'box', 'tip'] },
  { id: 'twoColumn',      label: '2 Columns',     description: 'Split into two columns.',  icon: Columns2,   keywords: ['2col', '2column', 'columns', 'split', 'layout', 'two', 'column', 'side'] },
] as const;

type SlashCommandId = (typeof SLASH_COMMANDS)[number]['id'];

const FONTS = [
  { label: 'Default', value: 'ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif, "Segoe UI Emoji", "Segoe UI Symbol"' },
  { label: 'Serif', value: 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif' },
  { label: 'Mono', value: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace' },
];

const FONT_SIZES = ['12px', '14px', '16px', '18px', '20px', '24px', '30px', '36px'];
const BLOCK_TYPE_OPTIONS = [
  { value: 'paragraph', label: 'Text' },
  { value: 'heading1', label: 'Heading 1' },
  { value: 'heading2', label: 'Heading 2' },
  { value: 'heading3', label: 'Heading 3' },
  { value: 'bulletList', label: 'Bulleted List' },
  { value: 'orderedList', label: 'Numbered List' },
  { value: 'blockquote', label: 'Quote' },
  { value: 'codeBlock', label: 'Code Block' },
] as const;

// ─────────────────────────────────────────────────────────────────────────────
// Custom Extensions
// ─────────────────────────────────────────────────────────────────────────────

const FontSize = Extension.create({
  name: 'fontSize',
  addOptions() { return { types: ['textStyle'] }; },
  // @ts-expect-error - addAttributes works in this Tiptap version
  addAttributes() {
    return {
      fontSize: {
        default: null,
        parseHTML: (element: any) => element.style.fontSize.replace(/['"]+/g, ''),
        renderHTML: (attributes: any) => {
          if (!attributes.fontSize) return {};
          return { style: `font-size: ${attributes.fontSize}` };
        },
      },
    };
  },
  addCommands() {
    return {
      setFontSize: (fontSize: string) => ({ chain }: any) => chain().setMark('textStyle', { fontSize }).run(),
      unsetFontSize: () => ({ chain }: any) => chain().setMark('textStyle', { fontSize: null }).removeEmptyTextStyle().run(),
    } as any;
  },
});

function getTopLevelBlockInfo(doc: Editor['state']['doc'], pos: number) {
  if (doc.childCount === 0) return null;
  const clampedPos = Math.max(0, Math.min(pos, doc.content.size));
  const $pos = doc.resolve(clampedPos);

  if ($pos.depth >= 1) {
    const blockPos = $pos.before(1);
    const block = doc.nodeAt(blockPos);
    if (block?.isBlock) return { blockPos, block, insertPos: blockPos + block.nodeSize };
  }

  const childIndex = clampedPos >= doc.content.size
    ? doc.childCount - 1
    : Math.min($pos.index(0), doc.childCount - 1);

  let offset = 0;
  for (let index = 0; index < childIndex; index += 1) {
    offset += doc.child(index).nodeSize;
  }

  const block = doc.child(childIndex);
  return { blockPos: offset, block, insertPos: offset + block.nodeSize };
}

function looksLikeSingleUrl(value: string): boolean {
  const text = value.trim();
  if (!text || /\s/.test(text)) return false;
  return /^(https?:\/\/|www\.)/i.test(text);
}

function getPreviewHostLabel(value: string): string {
  const text = value.trim();
  if (!text) return '';
  try {
    const parsed = new URL(/^https?:\/\//i.test(text) ? text : `https://${text}`);
    return parsed.hostname.replace(/^www\./i, '');
  } catch {
    return text.replace(/^https?:\/\//i, '').replace(/^www\./i, '');
  }
}

function getActiveBlockType(editor: Editor): (typeof BLOCK_TYPE_OPTIONS)[number]['value'] {
  if (editor.isActive('codeBlock')) return 'codeBlock';
  if (editor.isActive('blockquote')) return 'blockquote';
  if (editor.isActive('bulletList')) return 'bulletList';
  if (editor.isActive('orderedList')) return 'orderedList';
  if (editor.isActive('heading', { level: 1 })) return 'heading1';
  if (editor.isActive('heading', { level: 2 })) return 'heading2';
  if (editor.isActive('heading', { level: 3 })) return 'heading3';
  return 'paragraph';
}

// ─────────────────────────────────────────────────────────────────────────────
// Resizable image node
// ─────────────────────────────────────────────────────────────────────────────

function parseWidthPercent(width: unknown): number {
  if (typeof width === 'number' && Number.isFinite(width)) return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round(width)));
  if (typeof width !== 'string') return 100;
  const trimmed = width.trim().toLowerCase();
  if (!trimmed) return 100;
  if (trimmed.endsWith('%')) {
    const pct = Number(trimmed.replace('%', ''));
    if (Number.isFinite(pct)) return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round(pct)));
  }
  if (trimmed.endsWith('px')) {
    const px = Number(trimmed.replace('px', ''));
    if (Number.isFinite(px)) return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round((px / 960) * 100)));
  }
  const value = Number(trimmed);
  if (Number.isFinite(value)) return Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round(value)));
  return 100;
}

function normalizeWidth(width: unknown): string { return `${parseWidthPercent(width)}%`; }

function ResizableImageNode({ node, selected, updateAttributes, editor }: NodeViewProps) {
  const [isDragging, setIsDragging] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);

  useEffect(() => { return () => { cleanupRef.current?.(); cleanupRef.current = null; }; }, []);

  const startResize = useCallback(
    (event: ReactPointerEvent<HTMLButtonElement>) => {
      if (!editor.isEditable) return;
      event.preventDefault(); event.stopPropagation();

      const editorRoot = editor.view.dom as HTMLElement;
      const containerWidth = Math.max(editorRoot?.clientWidth || 1, 1);
      const startX = event.clientX;
      const initialPercent = parseWidthPercent(node.attrs.width);
      const initialPx = (initialPercent / 100) * containerWidth;

      let rafId = 0; let pendingPercent = initialPercent;
      const flush = () => { rafId = 0; updateAttributes({ width: pendingPercent }); };

      const onMove = (moveEvent: PointerEvent) => {
        const deltaX = moveEvent.clientX - startX;
        const nextPx = Math.max(containerWidth * (MIN_IMAGE_PERCENT / 100), Math.min(containerWidth, initialPx + deltaX));
        pendingPercent = Math.max(MIN_IMAGE_PERCENT, Math.min(MAX_IMAGE_PERCENT, Math.round((nextPx / containerWidth) * 100)));
        if (!rafId) rafId = window.requestAnimationFrame(flush);
      };

      const stop = () => {
        if (rafId) { window.cancelAnimationFrame(rafId); rafId = 0; }
        document.removeEventListener('pointermove', onMove); document.removeEventListener('pointerup', stop); document.removeEventListener('pointercancel', stop);
        cleanupRef.current = null; setIsDragging(false);
      };

      cleanupRef.current = stop; setIsDragging(true);
      document.addEventListener('pointermove', onMove); document.addEventListener('pointerup', stop); document.addEventListener('pointercancel', stop);
    },
    [editor, node.attrs.width, updateAttributes]
  );

  const width = normalizeWidth(node.attrs.width);

  return (
    <NodeViewWrapper as="span" data-note-image-node className={`notes-image-node ${selected ? 'is-selected' : ''} ${isDragging ? 'is-dragging' : ''}`} style={{ width }}>
      <img src={node.attrs.src} alt={node.attrs.alt || ''} title={node.attrs.title || ''} draggable={false} />
      {editor.isEditable && <button type="button" className="notes-image-handle" onPointerDown={startResize} title="Drag to resize image" aria-label="Drag to resize image" />}
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
        parseHTML: (element) => parseWidthPercent(element.getAttribute('data-width') || element.style.width || (element.getAttribute('width') ? `${element.getAttribute('width')}px` : '100%')),
        renderHTML: (attributes) => { const width = normalizeWidth(attributes.width); return { 'data-width': width, style: `width:${width};height:auto;` }; },
      },
    };
  },
  addNodeView() { return ReactNodeViewRenderer(ResizableImageNode); },
});

function LinkPreviewNodeView({ node, selected, deleteNode, editor }: NodeViewProps) {
  const kind = String(node.attrs.kind || 'link');
  const imageUrl = node.attrs.imageUrl as string | null;
  const title = node.attrs.title as string | null;
  const subtitle = node.attrs.subtitle as string | null;
  const description = node.attrs.description as string | null;
  const url = node.attrs.url as string;
  const provider = node.attrs.provider as string | null;
  const hostLabel = getPreviewHostLabel(url);
  const badgeLabel = provider || (kind === 'youtube' ? 'YouTube' : 'Link');

  return (
    <NodeViewWrapper contentEditable={false} className="my-4">
      <div
        className={`group relative overflow-hidden rounded-xl border bg-background transition-colors ${
          selected
            ? 'border-primary/35 ring-2 ring-primary/10'
            : 'border-border/60 hover:border-border hover:bg-foreground/[0.02]'
        }`}
      >
        <a href={url} target="_blank" rel="noopener noreferrer" className="flex flex-col sm:flex-row">
          <div className="relative border-b border-border/50 bg-foreground/[0.03] sm:min-h-[132px] sm:w-52 sm:border-b-0 sm:border-r">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={title || provider || hostLabel || url}
                className="block h-36 w-full object-cover sm:h-full"
                draggable={false}
              />
            ) : (
              <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">Preview unavailable</div>
            )}
            {kind === 'youtube' && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <div className="flex h-11 w-11 items-center justify-center rounded-full border border-border/60 bg-background/88 text-foreground shadow-sm">
                  <Play className="ml-0.5 h-4 w-4 fill-current" />
                </div>
              </div>
            )}
          </div>

          <div className="min-w-0 flex-1 px-4 py-3.5 sm:px-5">
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
              <span className="rounded-full border border-border/60 bg-foreground/[0.03] px-2 py-0.5 font-medium uppercase tracking-[0.16em] text-muted-foreground">
                {badgeLabel}
              </span>
              {hostLabel && <span className="truncate">{hostLabel}</span>}
            </div>
            <div className="mt-2 line-clamp-2 text-[15px] font-semibold leading-snug text-foreground">
              {title || hostLabel || url}
            </div>
            {subtitle && <div className="mt-1 text-[12px] text-muted-foreground">{subtitle}</div>}
            {description && (
              <div className="mt-2 line-clamp-2 text-[13px] leading-5 text-muted-foreground">
                {description}
              </div>
            )}
            <div className="mt-3 flex items-center gap-1.5 text-[12px] text-muted-foreground">
              <ExternalLink className="h-3.5 w-3.5" />
              <span className="truncate">{url}</span>
            </div>
          </div>
        </a>

        {editor.isEditable && (
          <button
            type="button"
            onClick={(event) => { event.preventDefault(); deleteNode(); }}
            className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-full border border-border/60 bg-background/92 text-muted-foreground shadow-sm transition-colors hover:border-border hover:bg-foreground/[0.05] hover:text-rose-400"
            title="Remove preview"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </NodeViewWrapper>
  );
}

const LinkPreviewBlock = Node.create({
  name: 'linkPreviewBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes() {
    return {
      url: {
        default: '',
        parseHTML: (element) => element.getAttribute('data-url') || '',
        renderHTML: (attributes) => ({ 'data-url': attributes.url || '' }),
      },
      kind: {
        default: 'link',
        parseHTML: (element) => element.getAttribute('data-kind') || 'link',
        renderHTML: (attributes) => ({ 'data-kind': attributes.kind || 'link' }),
      },
      provider: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-provider'),
        renderHTML: (attributes) => (attributes.provider ? { 'data-provider': attributes.provider } : {}),
      },
      title: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-title'),
        renderHTML: (attributes) => (attributes.title ? { 'data-title': attributes.title } : {}),
      },
      subtitle: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-subtitle'),
        renderHTML: (attributes) => (attributes.subtitle ? { 'data-subtitle': attributes.subtitle } : {}),
      },
      description: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-description'),
        renderHTML: (attributes) => (attributes.description ? { 'data-description': attributes.description } : {}),
      },
      imageUrl: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-image-url'),
        renderHTML: (attributes) => (attributes.imageUrl ? { 'data-image-url': attributes.imageUrl } : {}),
      },
    };
  },
  parseHTML() { return [{ tag: 'div[data-link-preview-block]' }]; },
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-link-preview-block': 'true' }, HTMLAttributes)];
  },
  addNodeView() { return ReactNodeViewRenderer(LinkPreviewNodeView); },
});

// ─────────────────────────────────────────────────────────────────────────────
// Chart block — renders a point-in-time Plotly snapshot
// ─────────────────────────────────────────────────────────────────────────────

function useDocTheme(): 'light' | 'dark' {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof document === 'undefined') return 'dark';
    return document.documentElement.classList.contains('light') ? 'light' : 'dark';
  });
  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => setTheme(root.classList.contains('light') ? 'light' : 'dark'));
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);
  return theme;
}

function ChartBlockNodeView({ node, selected, deleteNode, updateAttributes, editor }: NodeViewProps) {
  const theme = useDocTheme();
  const chartId = node.attrs.chartId as string;
  const figureJson = node.attrs.figureJson as string | null;
  const snapshotAt = node.attrs.snapshotAt as string | null;
  const chartHeight = (node.attrs.chartHeight as number) || 320;
  const plotRef = useRef<HTMLDivElement>(null);
  const resizeCleanupRef = useRef<(() => void) | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);

  const loadSnapshot = useCallback(async () => {
    if (!chartId) return;
    setSnapshotLoading(true); setSnapshotError(null);
    try {
      const res1 = await apiFetch(`/api/v1/dashboard/charts/${chartId}/figure`);
      if (res1.ok) { const data = await res1.json(); if (data?.figure && typeof data.figure === 'object') { updateAttributes({ figureJson: JSON.stringify(data.figure), snapshotAt: new Date().toISOString() }); return; } }
      const res2 = await apiFetch(`/api/custom/${chartId}`);
      if (res2.ok) { const data = await res2.json(); if (data?.figure) { updateAttributes({ figureJson: JSON.stringify(data.figure), snapshotAt: new Date().toISOString() }); return; } }
      const res3 = await apiFetch(`/api/custom/${chartId}/refresh`, { method: 'POST' });
      if (res3.ok) { const data = await res3.json(); if (data?.figure) { updateAttributes({ figureJson: JSON.stringify(data.figure), snapshotAt: new Date().toISOString() }); return; } }
      setSnapshotError('No figure data found.');
    } catch (err) { setSnapshotError(`Failed to load chart: ${err instanceof Error ? err.message : 'unknown error'}`); } finally { setSnapshotLoading(false); }
  }, [chartId, updateAttributes]);

  useEffect(() => { if (!figureJson && !snapshotError) loadSnapshot(); }, []);
  useEffect(() => { return () => { resizeCleanupRef.current?.(); resizeCleanupRef.current = null; }; }, []);

  useEffect(() => {
    if (!figureJson || !plotRef.current) return;
    let cancelled = false; let figure: any;
    try { figure = JSON.parse(figureJson); } catch { return; }
    const themed = applyChartTheme(figure, theme);
    (async () => {
      const Plotly = (await import('plotly.js-dist-min')) as any;
      if (cancelled || !plotRef.current) return;
      try { Plotly.purge(plotRef.current); } catch { }
      Plotly.react(plotRef.current, themed.data || [], themed.layout, { responsive: true, displayModeBar: false });
    })();
    return () => { cancelled = true; };
  }, [figureJson, chartHeight, theme]);

  const startHeightResize = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!editor.isEditable) return;
      event.preventDefault(); event.stopPropagation();
      const startY = event.clientY; const initialHeight = chartHeight;
      let rafId = 0; let pendingHeight = initialHeight;
      const flush = () => { rafId = 0; updateAttributes({ chartHeight: pendingHeight }); };
      const onMove = (e: PointerEvent) => { pendingHeight = Math.max(180, Math.min(900, initialHeight + (e.clientY - startY))); if (!rafId) rafId = window.requestAnimationFrame(flush); };
      const stop = () => { if (rafId) { window.cancelAnimationFrame(rafId); rafId = 0; } document.removeEventListener('pointermove', onMove); document.removeEventListener('pointerup', stop); document.removeEventListener('pointercancel', stop); resizeCleanupRef.current = null; };
      resizeCleanupRef.current = stop; document.addEventListener('pointermove', onMove); document.addEventListener('pointerup', stop); document.addEventListener('pointercancel', stop);
    },
    [editor.isEditable, chartHeight, updateAttributes]
  );

  const formattedDate = snapshotAt ? new Date(snapshotAt).toLocaleString([], { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : null;

  return (
    <NodeViewWrapper contentEditable={false}>
      <div className={`notes-chart-node ${selected ? 'is-selected ring-2 ring-sky-500/50' : ''} relative rounded-lg border border-border/40 overflow-hidden my-4 group`}>
        <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
          {editor.isEditable && <button type="button" className="p-1.5 rounded-md bg-background/80 hover:bg-rose-500/20 hover:text-rose-400 text-muted-foreground transition-colors shadow-sm backdrop-blur" onClick={deleteNode} title="Remove chart"><X className="w-4 h-4" /></button>}
        </div>

        {figureJson ? (
          <div ref={plotRef} style={{ width: '100%', height: chartHeight }} />
        ) : snapshotLoading ? (
          <div style={{ height: chartHeight }} className="relative flex flex-col items-center justify-center gap-3 rounded bg-foreground/[0.02] overflow-hidden">
            <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.6s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-foreground/[0.04] to-transparent" />
            <Loader2 className="w-5 h-5 animate-spin text-sky-500/50" />
            <span className="text-[11px] font-medium text-muted-foreground/50 tracking-wider uppercase">Loading chart snapshot...</span>
          </div>
        ) : (
          <div style={{ height: chartHeight }} className="flex flex-col items-center justify-center gap-3 bg-foreground/[0.02]">
            <span className="text-[12px] text-muted-foreground/60">{snapshotError ?? 'No snapshot data.'}</span>
            {editor.isEditable && <button type="button" onClick={loadSnapshot} className="px-4 py-1.5 text-[12px] font-medium rounded-md border border-border/50 text-foreground hover:bg-foreground/5 transition-colors">{snapshotError ? 'Retry' : 'Load snapshot'}</button>}
          </div>
        )}

        {formattedDate && (
          <div className="absolute bottom-2 left-2 text-[10px] text-muted-foreground/40 bg-background/60 px-1.5 py-0.5 rounded backdrop-blur">
            <Clock className="w-3 h-3 inline-block mr-1 opacity-50" />{formattedDate}
          </div>
        )}

        {editor.isEditable && <div className="absolute bottom-0 left-0 right-0 h-2 cursor-ns-resize hover:bg-sky-500/20 transition-colors" onPointerDown={startHeightResize} title="Drag to resize" />}
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
      chartId: { default: null, parseHTML: (el) => el.getAttribute('data-chart-id'), renderHTML: (attrs) => ({ 'data-chart-id': attrs.chartId || '' }) },
      chartName: { default: null, parseHTML: (el) => el.getAttribute('data-chart-name'), renderHTML: (attrs) => ({ 'data-chart-name': attrs.chartName || '' }) },
      figureJson: { default: null, parseHTML: (el) => el.getAttribute('data-figure') || null, renderHTML: (attrs) => (attrs.figureJson ? { 'data-figure': attrs.figureJson } : {}) },
      snapshotAt: { default: null, parseHTML: (el) => el.getAttribute('data-snapshot-at') || null, renderHTML: (attrs) => (attrs.snapshotAt ? { 'data-snapshot-at': attrs.snapshotAt } : {}) },
      chartHeight: { default: 320, parseHTML: (el) => { const v = el.getAttribute('data-chart-height'); return v ? Math.max(180, Math.min(900, Number(v))) : 320; }, renderHTML: (attrs) => ({ 'data-chart-height': String(attrs.chartHeight || 320) }) },
    };
  },
  parseHTML() { return [{ tag: 'div[data-chart-block]' }]; },
  renderHTML({ HTMLAttributes }) { return ['div', mergeAttributes({ 'data-chart-block': 'true' }, HTMLAttributes)]; },
  addNodeView() { return ReactNodeViewRenderer(ChartBlockNodeView); },
});

// ─────────────────────────────────────────────────────────────────────────────
// Two-column layout nodes
// ─────────────────────────────────────────────────────────────────────────────

const ColumnNode = Node.create({
  name: 'column',
  content: 'block+',
  isolating: true,
  renderHTML: ({ HTMLAttributes }) => ['div', mergeAttributes({ 'data-column': '' }, HTMLAttributes), 0],
  parseHTML: () => [{ tag: 'div[data-column]' }],
});

const TwoColumnBlock = Node.create({
  name: 'twoColumnBlock',
  group: 'block',
  content: 'column{2}',
  isolating: true,
  renderHTML: ({ HTMLAttributes }) => ['div', mergeAttributes({ 'data-two-column': '' }, HTMLAttributes), 0],
  parseHTML: () => [{ tag: 'div[data-two-column]' }],
});

const TrailingNode = Extension.create({
  name: 'trailingNode',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('trailingNode'),
        appendTransaction(_, __, state) {
          const { doc, tr, schema } = state;
          const last = doc.lastChild;
          if (last?.type.name === 'paragraph' && !last.content.size) return null;
          return tr.insert(doc.content.size, schema.nodes.paragraph.create());
        },
      }),
    ];
  },
});

// ─────────────────────────────────────────────────────────────────────────────
// Custom Dropdown Menu
// ─────────────────────────────────────────────────────────────────────────────

function CustomDropdownMenu({
  value,
  options,
  onChange,
  placeholder,
  renderValue,
  renderOption,
  dropdownWidth = 'w-32',
  style,
}: {
  value: string;
  options: { label: string; value: string }[];
  onChange: (v: string) => void;
  placeholder: React.ReactNode;
  renderValue?: (v: string) => React.ReactNode;
  renderOption?: (o: { label: string; value: string }) => React.ReactNode;
  dropdownWidth?: string;
  style?: CSSProperties;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as globalThis.Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [isOpen]);

  const selectedOption = options.find(o => o.value === value);

  return (
    <div ref={containerRef} className="relative inline-block text-left" style={style}>
      <button
        type="button"
        onMouseDown={(e) => { e.preventDefault(); setIsOpen(!isOpen); }}
        className={`flex items-center justify-between gap-1 h-8 px-2 rounded-md transition-colors text-[13px] font-medium min-w-[60px] ${isOpen ? 'bg-foreground/10 text-foreground' : 'hover:bg-foreground/5 text-foreground/90'}`}
      >
        <span className="truncate max-w-[100px]">
          {selectedOption ? (renderValue ? renderValue(selectedOption.value) : selectedOption.label) : placeholder}
        </span>
        <ChevronDown className="w-3 h-3 text-muted-foreground opacity-50 ml-1 shrink-0" />
      </button>

      {isOpen && (
        <div className={`absolute top-full left-0 mt-1 ${dropdownWidth} bg-background border border-border/40 rounded-lg shadow-xl backdrop-blur-xl z-[10000] py-1 max-h-64 overflow-y-auto custom-scrollbar`}>
          {options.map(opt => (
            <button
              key={opt.value}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(opt.value);
                setIsOpen(false);
              }}
              className={`w-full text-left px-3 py-1.5 text-[13px] hover:bg-foreground/5 flex items-center justify-between transition-colors ${value === opt.value ? 'bg-sky-500/10 text-sky-500 font-medium' : 'text-foreground/80'}`}
            >
              <span className="truncate pr-2">{renderOption ? renderOption(opt) : opt.label}</span>
              {value === opt.value && <Check className="w-3.5 h-3.5 shrink-0" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Slash command palette
// ─────────────────────────────────────────────────────────────────────────────

function SlashCommandMenu({ query, top, left, onSelect, onClose }: { query: string; top: number; left: number; onSelect: (id: SlashCommandId) => void; onClose: () => void; }) {
  const [index, setIndex] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const activeItemRef = useRef<HTMLButtonElement>(null);
  const [posStyle, setPosStyle] = useState<CSSProperties>({ position: 'fixed', top, left, zIndex: 9999, opacity: 0 });

  const filtered = useMemo(() => SLASH_COMMANDS.filter((cmd) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return cmd.label.toLowerCase().includes(q) || cmd.keywords.some((k) => k.includes(q));
  }), [query]);

  useEffect(() => { setIndex(0); }, [query]);
  useEffect(() => { activeItemRef.current?.scrollIntoView({ block: 'nearest' }); }, [index]);

  useLayoutEffect(() => {
    if (!menuRef.current) return;
    const rect = menuRef.current.getBoundingClientRect();
    const overflowsBottom = rect.bottom > window.innerHeight - 8;
    const clampedLeft = Math.max(8, Math.min(left, window.innerWidth - rect.width - 8));
    setPosStyle({ position: 'fixed', top: overflowsBottom ? undefined : top, bottom: overflowsBottom ? window.innerHeight - top : undefined, left: clampedLeft, zIndex: 9999, opacity: 1 });
  }, [top, left]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); e.stopPropagation(); setIndex((i) => (i + 1) % Math.max(1, filtered.length)); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation(); setIndex((i) => (i - 1 + Math.max(1, filtered.length)) % Math.max(1, filtered.length)); }
      else if (e.key === 'Enter' && filtered.length > 0) { e.preventDefault(); e.stopPropagation(); const cmd = filtered[index]; if (cmd) onSelect(cmd.id as SlashCommandId); }
      else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); onClose(); }
    };
    window.addEventListener('keydown', handler, { capture: true });
    return () => window.removeEventListener('keydown', handler, { capture: true });
  }, [filtered, index, onSelect, onClose]);

  if (!filtered.length) return null;

  return (
    <div ref={menuRef} style={posStyle} className="w-64 rounded-xl border border-border/40 bg-background/95 backdrop-blur-xl shadow-2xl overflow-hidden py-1">
      <div className="px-3 py-1.5 text-[10px] font-semibold text-muted-foreground/60">Basic blocks</div>
      <div className="max-h-64 overflow-y-auto px-1 custom-scrollbar">
        {filtered.map((cmd, i) => {
          const Icon = cmd.icon;
          return (
            <button key={cmd.id} ref={i === index ? activeItemRef : undefined} type="button" onMouseEnter={() => setIndex(i)} onMouseDown={(e) => { e.preventDefault(); onSelect(cmd.id as SlashCommandId); }} className={`w-full px-2 py-1.5 flex items-center gap-3 text-left transition-colors rounded-lg ${i === index ? 'bg-foreground/5 text-foreground' : 'text-muted-foreground hover:bg-foreground/5 hover:text-foreground'}`}>
              <div className="w-10 h-10 rounded border border-border/40 bg-background flex items-center justify-center shrink-0 shadow-sm"><Icon className="w-5 h-5 text-foreground/70" /></div>
              <div className="min-w-0 flex-1"><div className="text-[13px] font-medium leading-tight text-foreground/90">{cmd.label}</div><div className="text-[11px] text-muted-foreground/60 leading-tight mt-0.5">{cmd.description}</div></div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Chart picker
// ─────────────────────────────────────────────────────────────────────────────

function ChartPickerMenu({ chartLibrary, top, left, onSelect, onClose }: { chartLibrary: ChartItem[]; top: number; left: number; onSelect: (chart: ChartItem) => void; onClose: () => void; }) {
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const activeItemRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [posStyle, setPosStyle] = useState<CSSProperties>({ position: 'fixed', top, left, zIndex: 9999, opacity: 0 });

  useLayoutEffect(() => {
    if (!menuRef.current) return;
    const rect = menuRef.current.getBoundingClientRect();
    const overflowsBottom = rect.bottom > window.innerHeight - 8;
    const clampedLeft = Math.max(8, Math.min(left, window.innerWidth - rect.width - 8));
    setPosStyle({ position: 'fixed', top: overflowsBottom ? undefined : top, bottom: overflowsBottom ? window.innerHeight - top : undefined, left: clampedLeft, zIndex: 9999, opacity: 1 });
  }, [top, left]);

  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 30); }, []);

  const filtered = chartLibrary.filter((c) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (c.name || '').toLowerCase().includes(q) || (c.category || '').toLowerCase().includes(q);
  }).slice(0, 40);

  useEffect(() => { setActiveIndex(0); }, [query]);
  useEffect(() => { activeItemRef.current?.scrollIntoView({ block: 'nearest' }); }, [activeIndex]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); onClose(); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); e.stopPropagation(); setActiveIndex((i) => Math.min(i + 1, filtered.length - 1)); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation(); setActiveIndex((i) => Math.max(i - 1, 0)); return; }
      if (e.key === 'Enter' && filtered.length > 0) { e.preventDefault(); e.stopPropagation(); onSelect(filtered[activeIndex]); return; }
    };
    window.addEventListener('keydown', handler, { capture: true });
    return () => window.removeEventListener('keydown', handler, { capture: true });
  }, [onClose, onSelect, filtered, activeIndex]);

  return (
    <div ref={menuRef} style={posStyle} className="w-64 rounded-xl border border-border/40 bg-background/95 backdrop-blur-xl shadow-2xl overflow-hidden py-1">
      <div className="px-2 py-2 border-b border-border/30">
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
          <input ref={inputRef} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search charts..." className="w-full bg-foreground/[0.03] border border-border/40 rounded-lg pl-7 pr-2 py-1.5 text-[12px] focus:outline-none focus:border-sky-500/40 focus:ring-1 focus:ring-sky-500/10 transition-all placeholder:text-muted-foreground/40" />
        </div>
      </div>
      <div className="max-h-60 overflow-y-auto p-1 custom-scrollbar">
        {filtered.length === 0 && <div className="px-3 py-4 text-[12px] text-muted-foreground/50 text-center">No charts found.</div>}
        {filtered.map((chart, i) => (
          <button key={chart.id} ref={i === activeIndex ? activeItemRef : undefined} type="button" onMouseEnter={() => setActiveIndex(i)} onMouseDown={(e) => { e.preventDefault(); onSelect(chart); }} className={`w-full px-2 py-1.5 flex items-center gap-2.5 text-left transition-colors rounded-lg ${i === activeIndex ? 'bg-foreground/5' : 'hover:bg-foreground/5'}`}>
            <div className="w-7 h-7 rounded border border-border/40 bg-background flex items-center justify-center shrink-0 shadow-sm"><BarChart2 className="w-3.5 h-3.5 text-sky-500" /></div>
            <div className="min-w-0 flex-1"><span className="text-[13px] font-medium text-foreground truncate block leading-snug">{chart.name || chart.id}</span>{chart.category && <span className="text-[11px] text-muted-foreground/50 truncate block leading-none mt-0.5">{chart.category}</span>}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Editor component
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
  const theme = useDocTheme();
  const editorRef = useRef<Editor | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const slashStartPosRef = useRef<number | null>(null);
  const bubbleMenuRef = useRef<HTMLDivElement | null>(null);
  const draggedBlockPosRef = useRef<number | null>(null);

  const [slashMenu, setSlashMenu] = useState<{ query: string; top: number; left: number } | null>(null);
  const [chartPicker, setChartPicker] = useState<{ top: number; left: number } | null>(null);
  const [bubbleMenu, setBubbleMenu] = useState<{ top: number; left: number; isTable: boolean } | null>(null);
  const [blockHandle, setBlockHandle] = useState<{ top: number; left: number; insertPos: number; blockPos: number } | null>(null);
  const blockHideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleHideHandle = useCallback(() => {
    if (blockHideTimerRef.current) clearTimeout(blockHideTimerRef.current);
    blockHideTimerRef.current = setTimeout(() => setBlockHandle(null), 200);
  }, []);
  const cancelHideHandle = useCallback(() => {
    if (blockHideTimerRef.current) { clearTimeout(blockHideTimerRef.current); blockHideTimerRef.current = null; }
  }, []);

  useEffect(() => {
    if (!bubbleMenu) return;
    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as globalThis.Node | null;
      if (!target) return;
      if (bubbleMenuRef.current?.contains(target)) return;
      if (editorRef.current?.view.dom.contains(target)) return;
      setBubbleMenu(null);
    };
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [bubbleMenu]);

  const handleEditorMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const ed = editorRef.current;
    if (!ed || disabled) return;
    const view = ed.view;
    const containerRect = e.currentTarget.getBoundingClientRect();

    // If mouse is far left, keep handle visible
    if (e.clientX < containerRect.left + 50) return;

    const result = view.posAtCoords({ left: e.clientX, top: e.clientY });
    if (!result) { scheduleHideHandle(); return; }
    try {
      const blockInfo = getTopLevelBlockInfo(ed.state.doc, result.pos);
      if (!blockInfo) { scheduleHideHandle(); return; }

      const blockCoords = view.coordsAtPos(blockInfo.blockPos);
      cancelHideHandle();
      setBlockHandle({ top: blockCoords.top, left: containerRect.left, insertPos: blockInfo.insertPos, blockPos: blockInfo.blockPos });
    } catch { scheduleHideHandle(); }
  }, [disabled, scheduleHideHandle, cancelHideHandle]);

  const fetchLinkPreview = useCallback(async (url: string): Promise<LinkPreviewData> => {
    const normalizedUrl = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    return apiFetchJson<LinkPreviewData>(`/api/notes/link-preview?url=${encodeURIComponent(normalizedUrl)}`);
  }, []);

  const insertLinkPreviewAtSelection = useCallback(async (url: string, from: number, to: number) => {
    const ed = editorRef.current;
    if (!ed) return;
    try {
      const preview = await fetchLinkPreview(url);
      const attrs = {
        url: preview.url,
        kind: preview.kind || 'link',
        provider: preview.provider || null,
        title: preview.title || preview.url,
        subtitle: preview.subtitle || null,
        description: preview.description || null,
        imageUrl: preview.image_url || null,
      };
      ed.chain().focus().deleteRange({ from, to }).insertContent({ type: 'linkPreviewBlock', attrs }).run();
    } catch {
      ed.chain().focus().deleteRange({ from, to }).insertContent(url).run();
    }
  }, [fetchLinkPreview]);

  const uploadAndInsertImages = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        const optimized = await compressImageForUpload(file);
        const image = await onImageUpload(optimized);
        editorRef.current?.chain().focus().setImage({ src: image.url, alt: image.filename || file.name || 'image', width: 100 }).run();
      }
    },
    [onImageUpload]
  );

  const insertChartBlock = useCallback((chart: ChartItem) => {
    const ed = editorRef.current;
    if (!ed) return;
    const { from } = ed.state.selection;
    const startPos = slashStartPosRef.current;
    slashStartPosRef.current = null; setSlashMenu(null); setChartPicker(null);
    const attrs = { chartId: chart.id, chartName: chart.name || null, figureJson: null, snapshotAt: null, chartHeight: 320 };
    if (startPos !== null) {
      try { ed.chain().focus().deleteRange({ from: startPos, to: from }).insertContent({ type: 'chartBlock', attrs }).run(); }
      catch { ed.chain().focus().insertContent({ type: 'chartBlock', attrs }).run(); }
    } else { ed.chain().focus().insertContent({ type: 'chartBlock', attrs }).run(); }
  }, []);

  const applyBlockType = useCallback((nextType: (typeof BLOCK_TYPE_OPTIONS)[number]['value']) => {
    const ed = editorRef.current;
    if (!ed) return;
    const chain = ed.chain().focus().clearNodes();
    switch (nextType) {
      case 'heading1': chain.setHeading({ level: 1 }).run(); break;
      case 'heading2': chain.setHeading({ level: 2 }).run(); break;
      case 'heading3': chain.setHeading({ level: 3 }).run(); break;
      case 'bulletList': chain.toggleBulletList().run(); break;
      case 'orderedList': chain.toggleOrderedList().run(); break;
      case 'blockquote': chain.toggleBlockquote().run(); break;
      case 'codeBlock': chain.toggleCodeBlock().run(); break;
      default: chain.setParagraph().run(); break;
    }
  }, []);

  const executeSlashCommand = useCallback((id: SlashCommandId) => {
    const ed = editorRef.current;
    if (!ed) return;
    setSlashMenu(null);
    if (id === 'chart') {
      const coords = ed.view.coordsAtPos(ed.state.selection.from);
      setChartPicker({ top: coords.bottom, left: coords.left });
      return;
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
      case 'twoColumn':      ed.chain().focus().insertContent({ type: 'twoColumnBlock', content: [{ type: 'column', content: [{ type: 'paragraph' }] }, { type: 'column', content: [{ type: 'paragraph' }] }] }).run(); break;
    }
  }, []);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      Table.configure({ resizable: true }), TableRow, TableHeader, TableCell,
      FontFamily.configure({ types: ['textStyle'] }),
      TextStyle,
      FontSize,
      Link.configure({ openOnClick: false, autolink: true, linkOnPaste: true }),
      RichImage.configure({ allowBase64: false }),
      LinkPreviewBlock, ChartBlock, ColumnNode, TwoColumnBlock, TrailingNode,
      Placeholder.configure({ placeholder: "Type '/' for commands" }),
    ],
    content: value || '',
    editable: !disabled,
    onCreate: ({ editor }) => { editorRef.current = editor; },
    onDestroy: () => { editorRef.current = null; },
    onSelectionUpdate: ({ editor }) => {
      const { selection } = editor.state;
      if (disabled) { setBubbleMenu(null); return; }

      const isInTable = editor.isActive('table');
      const canFormatCurrentBlock = isInTable || !selection.empty;
      if (!canFormatCurrentBlock) { setBubbleMenu(null); return; }

      try {
        const from = selection.from;
        const to = selection.to;
        const startCoords = editor.view.coordsAtPos(from);
        const endCoords = editor.view.coordsAtPos(to);
        setBubbleMenu({ top: startCoords.top - 48, left: (startCoords.left + endCoords.left) / 2, isTable: isInTable });
      } catch { setBubbleMenu(null); }
    },
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
      if (disabled) return;
      const { selection } = editor.state;
      const { $from } = selection;
      if ($from.parent.type.name !== 'paragraph') { setSlashMenu(null); slashStartPosRef.current = null; return; }
      const textBefore = $from.parent.textContent.slice(0, $from.parentOffset);
      if (textBefore.startsWith('/') && !textBefore.includes(' ')) {
        const query = textBefore.slice(1).toLowerCase();
        const coords = editor.view.coordsAtPos(selection.from);
        if (slashStartPosRef.current === null) slashStartPosRef.current = selection.from - textBefore.length;
        setSlashMenu({ query, top: coords.bottom, left: coords.left });
      } else { setSlashMenu(null); slashStartPosRef.current = null; }
    },
    editorProps: {
      attributes: { class: `notes-editor-content px-4 py-2 focus:outline-none ${minHeightClassName}` },
      handleKeyDown: (view, event) => {
        if (event.key === 'Tab') {
          if (editorRef.current?.isActive('table')) {
            event.preventDefault();
            if (event.shiftKey) editorRef.current.commands.goToPreviousCell();
            else editorRef.current.commands.goToNextCell();
            return true;
          }
          event.preventDefault();
          const { state } = view;
          if (state.selection instanceof NodeSelection) {
            const endPos = state.selection.from + state.selection.node.nodeSize;
            editorRef.current?.commands.focus(Math.min(endPos, state.doc.content.size));
            return true;
          }
          if (state.selection.$from.node(-1)?.type.name === 'listItem') return false; // let list handle Tab
          if (state.selection.$from.parent.type.name === 'codeBlock') { view.dispatch(state.tr.insertText('\t')); return true; }
          view.dispatch(state.tr.insertText('    ')); return true;
        }
        return false;
      },
      handlePaste: (_view, event) => {
        if (disabled) return false;
        const pastedText = event.clipboardData?.getData('text/plain')?.trim() || '';
        if (looksLikeSingleUrl(pastedText)) {
          const selection = editorRef.current?.state.selection;
          if (selection) {
            event.preventDefault();
            void insertLinkPreviewAtSelection(pastedText, selection.from, selection.to);
            return true;
          }
        }
        const items = Array.from(event.clipboardData?.items || []);
        const files = items.filter((item) => item.type.startsWith('image/')).map((item) => item.getAsFile()).filter((file): file is File => !!file);
        if (!files.length) return false;
        event.preventDefault(); void uploadAndInsertImages(files); return true;
      },
      handleDrop: (view, event, _slice, moved) => {
        const draggedBlockPos = draggedBlockPosRef.current;
        if (!disabled && draggedBlockPos !== null && event.dataTransfer?.types.includes('application/x-investmentx-block')) {
          event.preventDefault();
          try {
            const draggedBlock = view.state.doc.nodeAt(draggedBlockPos);
            const dropCoords = view.posAtCoords({ left: event.clientX, top: event.clientY });
            if (!draggedBlock || !dropCoords) {
              draggedBlockPosRef.current = null;
              return true;
            }

            const targetInfo = getTopLevelBlockInfo(view.state.doc, dropCoords.pos);
            if (!targetInfo) {
              draggedBlockPosRef.current = null;
              return true;
            }

            const targetDom = view.nodeDOM(targetInfo.blockPos) as HTMLElement | null;
            let insertPos = targetInfo.blockPos;
            if (targetDom) {
              const rect = targetDom.getBoundingClientRect();
              insertPos = event.clientY > rect.top + (rect.height / 2) ? targetInfo.insertPos : targetInfo.blockPos;
            }

            if (insertPos >= draggedBlockPos && insertPos <= draggedBlockPos + draggedBlock.nodeSize) {
              draggedBlockPosRef.current = null;
              return true;
            }

            const transaction = view.state.tr.delete(draggedBlockPos, draggedBlockPos + draggedBlock.nodeSize);
            const adjustedInsertPos = insertPos > draggedBlockPos ? insertPos - draggedBlock.nodeSize : insertPos;
            transaction.insert(adjustedInsertPos, draggedBlock.copy(draggedBlock.content)).scrollIntoView();
            view.dispatch(transaction);
          } finally {
            draggedBlockPosRef.current = null;
          }
          return true;
        }

        if (disabled || moved) return false;
        const files = Array.from(event.dataTransfer?.files || []).filter((file) => file.type.startsWith('image/'));
        if (!files.length) return false;
        event.preventDefault(); void uploadAndInsertImages(files); return true;
      },
    },
  });

  useEffect(() => {
    if (!editor) return;
    const current = editor.getHTML();
    if ((value || '') !== current) editor.commands.setContent(value || '', { emitUpdate: false });
  }, [editor, value]);

  useEffect(() => { if (editor) editor.setEditable(!disabled); }, [editor, disabled]);

  const selectThemeStyle = useMemo(() => ({ colorScheme: theme }), [theme]);

  if (!editor) return null;

  const setLink = () => {
    const previousUrl = editor.getAttributes('link').href || '';
    const url = window.prompt('Enter link URL', previousUrl);
    if (url === null) return;
    if (url === '') { editor.chain().focus().unsetLink().run(); return; }
    const href = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    editor.chain().focus().extendMarkRange('link').setLink({ href }).run();
  };

  const handleBlockDragStart = (event: React.DragEvent<HTMLButtonElement>) => {
    if (!blockHandle) return;
    draggedBlockPosRef.current = blockHandle.blockPos;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('application/x-investmentx-block', String(blockHandle.blockPos));
    const blockSelection = NodeSelection.create(editor.state.doc, blockHandle.blockPos);
    editor.view.dispatch(editor.state.tr.setSelection(blockSelection));
    cancelHideHandle();
  };

  const handleBlockDragEnd = () => {
    draggedBlockPosRef.current = null;
    scheduleHideHandle();
  };

  const btnClass = "flex h-8 w-8 items-center justify-center rounded-md border border-transparent text-muted-foreground transition-colors hover:border-border/70 hover:bg-foreground/[0.05] hover:text-foreground";
  const activeBtnClass = "flex h-8 w-8 items-center justify-center rounded-md border border-border/70 bg-foreground/[0.06] text-foreground";

  return (
    <div className="relative">
      <style dangerouslySetInnerHTML={{__html: `
        .notes-editor-content {
          font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif, "Segoe UI Emoji", "Segoe UI Symbol";
          line-height: 1.6;
          color: rgb(var(--foreground));
        }
        .notes-editor-content p { margin-top: 4px; margin-bottom: 4px; min-height: 1.5em; }
        .notes-editor-content p.is-editor-empty:first-child::before {
          content: attr(data-placeholder);
          float: left;
          color: #9CA3AF;
          pointer-events: none;
          height: 0;
        }
        .notes-editor-content h1 { font-size: 2.25em; font-weight: 700; margin-top: 1.2em; margin-bottom: 0.2em; line-height: 1.2; letter-spacing: -0.02em; }
        .notes-editor-content h2 { font-size: 1.5em; font-weight: 600; margin-top: 1em; margin-bottom: 0.2em; line-height: 1.3; letter-spacing: -0.01em; }
        .notes-editor-content h3 { font-size: 1.25em; font-weight: 600; margin-top: 1em; margin-bottom: 0.2em; line-height: 1.3; }
        .notes-editor-content ul { padding-left: 1.2em; list-style-type: disc; margin: 0.2em 0; }
        .notes-editor-content ol { padding-left: 1.2em; list-style-type: decimal; margin: 0.2em 0; }
        .notes-editor-content li p { margin-top: 0; margin-bottom: 0; }
        .notes-editor-content blockquote {
          border-left: 3px solid rgb(var(--foreground));
          padding-left: 1em;
          margin-left: 0;
          margin-right: 0;
          font-style: italic;
          opacity: 0.8;
        }
        .notes-editor-content hr { border: none; border-top: 1px solid rgba(var(--border), 0.5); margin: 2em 0; }
        .notes-editor-content pre {
          background: rgba(var(--foreground), 0.05);
          border-radius: 6px;
          padding: 1em;
          font-family: ui-monospace, monospace;
          font-size: 0.9em;
          overflow-x: auto;
        }
        .notes-editor-content a { color: #38bdf8; text-decoration: none; border-bottom: 1px solid rgba(56, 189, 248, 0.4); transition: border-color 0.15s; }
        .notes-editor-content a:hover { border-bottom-color: #38bdf8; }

        .notes-toolbar-select {
          height: 2rem;
          min-width: 0;
          padding: 0 1.75rem 0 0.7rem;
          border: 1px solid rgba(var(--border), 0.6);
          border-radius: 0.7rem;
          background-color: rgba(var(--background), 0.96);
          color: rgb(var(--foreground));
          font-size: 13px;
          font-weight: 500;
          outline: none;
          cursor: pointer;
          appearance: none;
          transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, color 0.15s ease;
          background-image:
            linear-gradient(45deg, transparent 50%, rgba(var(--muted-foreground), 0.85) 50%),
            linear-gradient(135deg, rgba(var(--muted-foreground), 0.85) 50%, transparent 50%);
          background-position:
            calc(100% - 14px) calc(50% - 3px),
            calc(100% - 9px) calc(50% - 3px);
          background-size: 5px 5px, 5px 5px;
          background-repeat: no-repeat;
        }
        .notes-toolbar-select:hover {
          background-color: rgba(var(--foreground), 0.04);
          border-color: rgba(var(--border), 0.92);
        }
        .notes-toolbar-select:focus {
          border-color: rgba(var(--ring), 0.5);
          box-shadow: 0 0 0 2px rgba(var(--ring), 0.14);
        }
        .notes-toolbar-select option {
          background-color: rgb(var(--background));
          color: rgb(var(--foreground));
        }
        html.light .notes-toolbar-select {
          background-color: rgba(var(--card), 0.98);
        }

        /* Notion Style Tables */
        .notes-editor-content table {
          border-collapse: collapse;
          margin: 1em 0;
          overflow: hidden;
          table-layout: fixed;
          width: 100%;
        }
        .notes-editor-content table td, .notes-editor-content table th {
          min-width: 1em;
          border: 1px solid rgba(var(--border), 0.5);
          padding: 8px 10px;
          vertical-align: top;
          box-sizing: border-box;
          position: relative;
        }
        .notes-editor-content table th {
          background-color: rgba(var(--foreground), 0.03);
          font-weight: 600;
          text-align: left;
        }
        .notes-editor-content table .selectedCell:after {
          z-index: 2;
          position: absolute;
          content: "";
          left: 0; right: 0; top: 0; bottom: 0;
          background: rgba(56, 189, 248, 0.15);
          pointer-events: none;
        }
      `}} />

      {/* Notion-style Floating Formatting Bubble */}
      {bubbleMenu && !disabled && (
        <div
          ref={bubbleMenuRef}
          style={{ position: 'fixed', top: bubbleMenu.top, left: bubbleMenu.left, transform: 'translateX(-50%)', zIndex: 9998 }}
          onMouseDown={(e) => {
            const target = e.target as HTMLElement;
            if (target.closest('select')) return;
            e.preventDefault();
          }}
          className="flex items-center gap-1 rounded-xl border border-border/60 bg-background px-1.5 py-1 shadow-xl"
        >
          {/* Table Controls (if in table) */}
          {bubbleMenu.isTable && (
            <>
              <button type="button" onClick={() => editor.chain().focus().addColumnAfter().run()} className="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-foreground/[0.05] hover:text-foreground" title="Add Column Right"><Columns2 className="w-4 h-4" /> Add Col</button>
              <button type="button" onClick={() => editor.chain().focus().addRowAfter().run()} className="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-foreground/[0.05] hover:text-foreground" title="Add Row Below"><Rows2 className="w-4 h-4" /> Add Row</button>
              <div className="w-px h-5 bg-border/50 mx-1" />
              <button type="button" onClick={() => editor.chain().focus().deleteColumn().run()} className="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-rose-500/10 hover:text-rose-400" title="Delete Column"><Trash2 className="w-4 h-4" /> Col</button>
              <button type="button" onClick={() => editor.chain().focus().deleteRow().run()} className="flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-rose-500/10 hover:text-rose-400" title="Delete Row"><Trash2 className="w-4 h-4" /> Row</button>
              <button type="button" onClick={() => editor.chain().focus().deleteTable().run()} className="flex h-8 w-8 items-center justify-center rounded-md text-rose-500 transition-colors hover:bg-rose-500/10" title="Delete Table"><TableIcon className="w-4 h-4" /></button>
              {!editor.state.selection.empty && <div className="w-px h-5 bg-border/50 mx-1" />}
            </>
          )}

          <CustomDropdownMenu
            value={getActiveBlockType(editor)}
            options={BLOCK_TYPE_OPTIONS.map(o => ({ label: o.label, value: o.value }))}
            onChange={(v) => applyBlockType(v as any)}
            placeholder="Text"
            dropdownWidth="w-36"
            style={selectThemeStyle}
          />

          {!editor.state.selection.empty && <div className="w-px h-5 bg-border/50 mx-1" />}

          {/* Text Controls (if text is selected) */}
          {!editor.state.selection.empty && (
            <>
              {/* Font Type */}
              <CustomDropdownMenu
                value={editor.getAttributes('textStyle').fontFamily || ''}
                options={[{ label: 'Default Font', value: '' }, ...FONTS]}
                onChange={(v) => { if (!v) editor.chain().focus().unsetFontFamily().run(); else editor.chain().focus().setFontFamily(v).run(); }}
                placeholder="Default Font"
                dropdownWidth="w-40"
                renderOption={(opt) => <span style={{ fontFamily: opt.value || undefined, fontSize: '14px' }}>{opt.label}</span>}
                renderValue={(v) => {
                  const label = [{ label: 'Default Font', value: '' }, ...FONTS].find(f => f.value === v)?.label || 'Default Font';
                  return <span style={{ fontFamily: v || undefined }}>{label}</span>;
                }}
                style={selectThemeStyle}
              />

              <div className="w-px h-5 bg-border/50 mx-1" />

              {/* Font Size */}
              <CustomDropdownMenu
                value={editor.getAttributes('textStyle').fontSize || ''}
                options={[{ label: 'Size', value: '' }, ...FONT_SIZES.map(s => ({ label: s, value: s }))]}
                onChange={(v) => { if (!v) (editor.commands as any).unsetFontSize(); else (editor.commands as any).setFontSize(v); }}
                placeholder="Size"
                dropdownWidth="w-20"
                style={selectThemeStyle}
              />

              <div className="w-px h-5 bg-border/50 mx-1" />

              <button type="button" onClick={() => editor.chain().focus().toggleBold().run()} className={editor.isActive('bold') ? activeBtnClass : btnClass} title="Bold"><Bold className="w-4 h-4" /></button>
              <button type="button" onClick={() => editor.chain().focus().toggleItalic().run()} className={editor.isActive('italic') ? activeBtnClass : btnClass} title="Italic"><Italic className="w-4 h-4" /></button>
              <button type="button" onClick={() => editor.chain().focus().toggleStrike().run()} className={editor.isActive('strike') ? activeBtnClass : btnClass} title="Strikethrough"><span className="text-[14px] font-semibold line-through">S</span></button>
              <button type="button" onClick={() => editor.chain().focus().toggleCodeBlock().run()} className={editor.isActive('codeBlock') ? activeBtnClass : btnClass} title="Code Block"><Code2 className="w-4 h-4" /></button>
              <button type="button" onClick={setLink} className={editor.isActive('link') ? activeBtnClass : btnClass} title="Link"><LinkIcon className="w-4 h-4" /></button>
            </>
          )}
        </div>
      )}

      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={async (event: ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; event.target.value = ''; if (!file || !editor || disabled) return; try { await uploadAndInsertImages([file]); } catch { } }} />

      <div className="notes-editor" onMouseMove={handleEditorMouseMove} onMouseLeave={scheduleHideHandle}><EditorContent editor={editor} /></div>

      {/* Notion-style Left Gutter Block Handle */}
      {blockHandle && !disabled && (
        <div
          style={{ position: 'fixed', top: blockHandle.top + 2, left: blockHandle.left - 44, zIndex: 200 }}
          onMouseEnter={cancelHideHandle}
          onMouseLeave={scheduleHideHandle}
          onMouseDown={(e) => {
            const target = e.target as HTMLElement;
            if (target.closest('[draggable="true"]')) return;
            e.preventDefault();
          }}
          className="flex items-center gap-0.5"
        >
          <button type="button" onClick={() => { const { insertPos } = blockHandle; editor.chain().insertContentAt(insertPos, { type: 'paragraph' }).setTextSelection(insertPos + 1).insertContent('/').run(); setBlockHandle(null); }} className="w-6 h-6 rounded hover:bg-foreground/10 flex items-center justify-center text-muted-foreground/40 hover:text-foreground transition-colors" title="Click to add below"><Plus className="w-4 h-4" /></button>
          <button
            type="button"
            draggable
            onDragStart={handleBlockDragStart}
            onDragEnd={handleBlockDragEnd}
            className="w-4 h-6 rounded hover:bg-foreground/10 flex items-center justify-center text-muted-foreground/40 hover:text-foreground transition-colors cursor-grab active:cursor-grabbing"
            title="Drag to move block"
          >
            <GripVertical className="w-4 h-4" />
          </button>
        </div>
      )}

      {slashMenu && !disabled && <SlashCommandMenu query={slashMenu.query} top={slashMenu.top} left={slashMenu.left} onSelect={executeSlashCommand} onClose={() => { setSlashMenu(null); slashStartPosRef.current = null; }} />}
      {chartPicker && !disabled && <ChartPickerMenu chartLibrary={chartLibrary} top={chartPicker.top} left={chartPicker.left} onSelect={insertChartBlock} onClose={() => { setChartPicker(null); slashStartPosRef.current = null; editorRef.current?.commands.focus(); }} />}
    </div>
  );
}

async function compressImageForUpload(file: File): Promise<File> {
  if (typeof window === 'undefined' || !file.type.startsWith('image/') || file.size <= MAX_DIRECT_UPLOAD_BYTES || typeof createImageBitmap !== 'function') return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.max(bitmap.width, bitmap.height) > MAX_UPLOAD_EDGE ? MAX_UPLOAD_EDGE / Math.max(bitmap.width, bitmap.height) : 1;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale); canvas.height = Math.round(bitmap.height * scale);
    const ctx = canvas.getContext('2d'); if (!ctx) { bitmap.close(); return file; }
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height); bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/webp', 0.82));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], `${file.name.replace(/\.[^/.]+$/, '')}.webp`, { type: 'image/webp' });
  } catch { return file; }
}

export default memo(NotesRichEditor);
