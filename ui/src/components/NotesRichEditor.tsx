'use client';

import {
  type ChangeEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
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
import { FontFamily, FontSize, TextStyle } from '@tiptap/extension-text-style';
import { Table, TableRow, TableHeader, TableCell } from '@tiptap/extension-table';
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Heading1,
  Heading2,
  Square,
  Code2,
  Minus,
  Link as LinkIcon,
  Image as ImageIcon,
  Table as TableIcon,
  Undo2,
  Redo2,
} from 'lucide-react';

type UploadResult = {
  url: string;
  filename?: string | null;
};

type ExternalImageInsertRequest = {
  token: string;
  url: string;
  alt?: string;
};

interface NotesRichEditorProps {
  value: string;
  onChange: (html: string) => void;
  disabled?: boolean;
  onImageUpload: (file: File) => Promise<UploadResult>;
  externalImageInsertRequest?: ExternalImageInsertRequest | null;
  minHeightClassName?: string;
  toolbarStickyTopClassName?: string;
}

const MAX_UPLOAD_EDGE = 2200;
const MAX_DIRECT_UPLOAD_BYTES = 1_800_000;
const MIN_IMAGE_PERCENT = 20;
const MAX_IMAGE_PERCENT = 100;

const FONT_FAMILY_OPTIONS = [
  { label: 'Default', value: '' },
  { label: 'Inter', value: "'Inter', sans-serif" },
  { label: 'Outfit', value: "'Outfit', sans-serif" },
  { label: 'Georgia', value: 'Georgia, serif' },
  {
    label: 'Monospace',
    value:
      "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
] as const;

const FONT_SIZE_OPTIONS = [
  { label: 'Default', value: '' },
  { label: '12', value: '12px' },
  { label: '14', value: '14px' },
  { label: '16', value: '16px' },
  { label: '18', value: '18px' },
  { label: '20', value: '20px' },
  { label: '24', value: '24px' },
] as const;

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
        if (!rafId) {
          rafId = window.requestAnimationFrame(flush);
        }
      };

      const stop = () => {
        if (rafId) {
          window.cancelAnimationFrame(rafId);
          rafId = 0;
        }
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
          return {
            'data-width': width,
            style: `width:${width};height:auto;`,
          };
        },
      },
    };
  },
  addNodeView() {
    return ReactNodeViewRenderer(ResizableImageNode);
  },
});

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
    if (!ctx) {
      bitmap.close();
      return file;
    }
    ctx.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();

    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, 'image/webp', 0.82);
    });
    if (!blob || blob.size >= file.size) {
      return file;
    }

    const baseName = (file.name || 'image').replace(/\.[^/.]+$/, '');
    return new File([blob], `${baseName || 'image'}.webp`, {
      type: 'image/webp',
    });
  } catch {
    return file;
  }
}

function ToolbarButton({
  active,
  onClick,
  disabled,
  children,
  title,
}: {
  active?: boolean;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`h-6 px-1.5 rounded-md border text-[11px] inline-flex items-center gap-1 transition-colors ${
        active
          ? 'border-sky-500/40 bg-sky-500/15 text-sky-200'
          : 'border-border/50 text-muted-foreground hover:text-foreground hover:bg-accent/10'
      } disabled:opacity-40`}
    >
      {children}
    </button>
  );
}

function ToolbarSelect({
  value,
  onChange,
  disabled,
  title,
  options,
  className = '',
}: {
  value: string;
  onChange: (event: ChangeEvent<HTMLSelectElement>) => void;
  disabled?: boolean;
  title?: string;
  options: ReadonlyArray<{ label: string; value: string }>;
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={onChange}
      disabled={disabled}
      title={title}
      className={`h-6 px-1.5 rounded-md border border-border/50 bg-background/60 text-[11px] text-muted-foreground outline-none hover:text-foreground focus:ring-2 focus:ring-sky-500/20 disabled:opacity-40 ${className}`}
    >
      {options.map((option) => (
        <option key={option.label} value={option.value} className="bg-background text-foreground">
          {option.label}
        </option>
      ))}
    </select>
  );
}

export default function NotesRichEditor({
  value,
  onChange,
  disabled = false,
  onImageUpload,
  externalImageInsertRequest = null,
  minHeightClassName = 'min-h-[48vh]',
  toolbarStickyTopClassName = 'top-0',
}: NotesRichEditorProps) {
  const editorRef = useRef<Editor | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const lastExternalImageInsertTokenRef = useRef<string | null>(null);

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
          .setImage({
            src: image.url,
            alt: image.filename || file.name || 'image',
            width: 100,
          })
          .run();
      }
    },
    [onImageUpload]
  );

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit,
      TextStyle,
      FontFamily.configure({
        types: ['textStyle'],
      }),
      FontSize.configure({
        types: ['textStyle'],
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      Link.configure({
        openOnClick: false,
        autolink: true,
        linkOnPaste: true,
      }),
      RichImage.configure({
        allowBase64: false,
      }),
      Placeholder.configure({
        placeholder: 'Write your note... paste images and drag the handle to resize.',
      }),
    ],
    content: value || '',
    editable: !disabled,
    onCreate: ({ editor }) => {
      editorRef.current = editor;
    },
    onDestroy: () => {
      editorRef.current = null;
    },
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
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

  useEffect(() => {
    if (!editor || !externalImageInsertRequest) return;
    if (lastExternalImageInsertTokenRef.current === externalImageInsertRequest.token) return;
    lastExternalImageInsertTokenRef.current = externalImageInsertRequest.token;

    editor
      .chain()
      .focus()
      .setImage({
        src: externalImageInsertRequest.url,
        alt: externalImageInsertRequest.alt || 'chart snapshot',
        width: 100,
      })
      .insertContent('<p></p>')
      .run();
  }, [editor, externalImageInsertRequest]);

  const setLink = () => {
    if (!editor || disabled) return;
    const previousUrl = editor.getAttributes('link').href || '';
    const url = window.prompt('Enter URL', previousUrl);
    if (url === null) return;
    if (url === '') {
      editor.chain().focus().unsetLink().run();
      return;
    }
    const href = /^https?:\/\//i.test(url) ? url : `https://${url}`;
    editor.chain().focus().extendMarkRange('link').setLink({ href }).run();
  };

  const activeTextStyle = editor?.getAttributes('textStyle') || {};
  const activeFontFamily =
    typeof activeTextStyle.fontFamily === 'string' ? activeTextStyle.fontFamily : '';
  const activeFontSize = typeof activeTextStyle.fontSize === 'string' ? activeTextStyle.fontSize : '';
  const selectedFontFamily = FONT_FAMILY_OPTIONS.some((option) => option.value === activeFontFamily)
    ? activeFontFamily
    : '';
  const selectedFontSize = FONT_SIZE_OPTIONS.some((option) => option.value === activeFontSize)
    ? activeFontSize
    : '';

  const handleFontFamilyChange = (event: ChangeEvent<HTMLSelectElement>) => {
    if (!editor || disabled) return;
    const nextFamily = event.target.value;
    if (!nextFamily) {
      editor.chain().focus().unsetFontFamily().removeEmptyTextStyle().run();
      return;
    }
    editor.chain().focus().setFontFamily(nextFamily).run();
  };

  const handleFontSizeChange = (event: ChangeEvent<HTMLSelectElement>) => {
    if (!editor || disabled) return;
    const nextSize = event.target.value;
    if (!nextSize) {
      editor.chain().focus().setMark('textStyle', { fontSize: null }).removeEmptyTextStyle().run();
      return;
    }
    editor.chain().focus().setMark('textStyle', { fontSize: nextSize }).run();
  };

  const insertBox = () => {
    if (!editor || disabled) return;
    editor
      .chain()
      .focus()
      .insertContent('<blockquote><p>Box note</p></blockquote><p></p>')
      .run();
  };

  const insertTable = () => {
    if (!editor || disabled) return;
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  };

  const triggerImagePick = () => {
    fileInputRef.current?.click();
  };

  const onImageSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !editor || disabled) return;
    try {
      await uploadAndInsertImages([file]);
    } catch {
      // Parent manages error state.
    }
  };

  if (!editor) return null;

  return (
    <div className="space-y-2">
      <div
        className={`sticky ${toolbarStickyTopClassName} z-20 -mx-1 px-1 py-1.5 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 border-b border-border/40`}
      >
        <div className="flex items-center gap-1 flex-wrap">
          <ToolbarSelect
            value={selectedFontFamily}
            onChange={handleFontFamilyChange}
            disabled={disabled}
            title="Font Family"
            options={FONT_FAMILY_OPTIONS}
            className="w-[108px]"
          />
          <ToolbarSelect
            value={selectedFontSize}
            onChange={handleFontSizeChange}
            disabled={disabled}
            title="Font Size"
            options={FONT_SIZE_OPTIONS}
            className="w-[70px]"
          />
          <div className="w-px h-4 bg-border/50 mx-0.5" />
          <ToolbarButton onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} disabled={disabled} title="Bold">
            <Bold className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} disabled={disabled} title="Italic">
            <Italic className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} disabled={disabled} title="Heading 1">
            <Heading1 className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} disabled={disabled} title="Heading 2">
            <Heading2 className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} disabled={disabled} title="Bullet List">
            <List className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} disabled={disabled} title="Ordered List">
            <ListOrdered className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={insertBox} disabled={disabled} title="Insert Box">
            <Square className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={insertTable} disabled={disabled} title="Insert Table">
            <TableIcon className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().toggleCodeBlock().run()} active={editor.isActive('codeBlock')} disabled={disabled} title="Code Block">
            <Code2 className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().setHorizontalRule().run()} disabled={disabled} title="Divider">
            <Minus className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={setLink} active={editor.isActive('link')} disabled={disabled} title="Link">
            <LinkIcon className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={triggerImagePick} disabled={disabled} title="Upload Image">
            <ImageIcon className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().undo().run()} disabled={disabled || !editor.can().undo()} title="Undo">
            <Undo2 className="w-3.5 h-3.5" />
          </ToolbarButton>
          <ToolbarButton onClick={() => editor.chain().focus().redo().run()} disabled={disabled || !editor.can().redo()} title="Redo">
            <Redo2 className="w-3.5 h-3.5" />
          </ToolbarButton>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={onImageSelected}
      />

      <div className="notes-editor rounded-lg border border-border/60 bg-background/40 px-3 py-2">
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
