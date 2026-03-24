'use client';
import { Component, type ReactNode } from 'react';

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; error: string; }

export class ChartErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: '' };
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex items-center justify-center p-8 text-muted-foreground">
          <div className="text-center">
            <p className="text-sm font-medium">Chart rendering failed</p>
            <p className="text-xs mt-1 opacity-60">{this.state.error}</p>
            <button onClick={() => this.setState({ hasError: false, error: '' })}
              className="mt-3 text-xs px-3 py-1 rounded border border-border hover:bg-muted">
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
