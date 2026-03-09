'use client';

import React from 'react';
import { useChartEditor } from '@/hooks/useChartEditor';
import ActivityBar from './ActivityBar';
import SidebarPanel from './SidebarPanel';
import WorkspaceHeader from './WorkspaceHeader';
import PropertiesDrawer from './PropertiesDrawer';
import PreviewPanel from './PreviewPanel';
import EditorPanel from './EditorPanel';
import DeleteModal from './DeleteModal';
import PdfNotification from './PdfNotification';

interface CustomChartEditorProps {
  mode?: 'standalone' | 'integrated';
  initialChartId?: string | null;
  onClose?: () => void;
}

export default function CustomChartEditor({ mode = 'standalone', initialChartId, onClose }: CustomChartEditorProps) {
  const state = useChartEditor({ mode, initialChartId, onClose });

  return (
    <div className={`flex w-full overflow-hidden bg-background ${mode === 'standalone' ? 'h-full' : 'h-full border-l border-border/50 shadow-2xl z-50'}`}>
      {/* Activity Bar (VS Code Style) */}
      {mode === 'standalone' && (
        <ActivityBar
          activeTab={state.activeTab}
          libraryOpen={state.libraryOpen}
          name={state.name}
          setActiveTab={state.setActiveTab}
          setLibraryOpen={state.setLibraryOpen}
        />
      )}

      {/* Sidebar Panel */}
      {mode === 'standalone' && (
        <SidebarPanel state={state} />
      )}

      {/* Center Workspace */}
      <main className="flex-grow flex flex-col min-w-0 bg-background relative">
        <WorkspaceHeader
          name={state.name}
          setName={state.setName}
          category={state.category}
          createdByLabel={state.createdByLabel}
          canEditCurrentChart={state.canEditCurrentChart}
          loading={state.loading}
          saving={state.saving}
          showMeta={state.showMeta}
          setShowMeta={state.setShowMeta}
          showCodePanel={state.showCodePanel}
          toggleCodePanel={state.toggleCodePanel}
          handlePreview={state.handlePreview}
          handleSave={state.handleSave}
          mode={mode}
          onClose={onClose}
        />

        <PropertiesDrawer
          showMeta={state.showMeta}
          mode={mode}
          category={state.category}
          setCategory={state.setCategory}
          tags={state.tags}
          setTags={state.setTags}
          description={state.description}
          setDescription={state.setDescription}
          createdByLabel={state.createdByLabel}
          canEditCurrentChart={state.canEditCurrentChart}
          exportPdf={state.exportPdf}
          setExportPdf={state.setExportPdf}
          canToggleExport={state.canToggleExport}
          currentChartId={state.currentChartId}
          toggleExportPdf={state.toggleExportPdf}
        />

        {/* Workspace Canvas Area */}
        <div className="flex-grow flex flex-col relative min-h-0 overflow-hidden">
          {!state.showCodePanel ? (
            <PreviewPanel
              currentChartId={state.currentChartId}
              theme={state.theme}
              themedPreviewFigure={state.themedPreviewFigure}
              previewFigure={state.previewFigure}
              plotRenderError={state.plotRenderError}
              setPlotRenderError={state.setPlotRenderError}
              plotRetryNonce={state.plotRetryNonce}
              setPlotRetryNonce={state.setPlotRetryNonce}
              loadingChartId={state.loadingChartId}
              copying={state.copying}
              handleCopyChart={state.handleCopyChart}
              handlePlotError={state.handlePlotError}
            />
          ) : (
            <EditorPanel
              code={state.code}
              setCode={state.setCode}
              codeEditorRef={state.codeEditorRef}
              savedCursorPos={state.savedCursorPos}
              isLight={state.isLight}
              editorFontSize={state.editorFontSize}
              editorFontFamily={state.editorFontFamily}
              isMounted={state.isMounted}
              timeseriesSearch={state.timeseriesSearch}
              setTimeseriesSearch={state.setTimeseriesSearch}
              timeseriesQuery={state.timeseriesQuery}
              setTimeseriesQuery={state.setTimeseriesQuery}
              timeseriesMatches={state.timeseriesMatches}
              timeseriesLoading={state.timeseriesLoading}
              runTimeseriesSearch={state.runTimeseriesSearch}
              insertSeriesSnippet={state.insertSeriesSnippet}
              copySeriesSnippet={state.copySeriesSnippet}
              error={state.error}
              successMsg={state.successMsg}
              consoleExpanded={state.consoleExpanded}
              setConsoleExpanded={state.setConsoleExpanded}
              userManuallyCollapsed={state.userManuallyCollapsed}
              setUserManuallyCollapsed={state.setUserManuallyCollapsed}
            />
          )}
        </div>
      </main>

      {/* Notification Layer */}
      <PdfNotification pdfStatus={state.pdfStatus} pdfCount={state.pdfCount} />

      {/* Delete Confirmation Modal */}
      <DeleteModal
        deleteConfirm={state.deleteConfirm}
        setDeleteConfirm={state.setDeleteConfirm}
        deleteMutation={state.deleteMutation}
      />
    </div>
  );
}
