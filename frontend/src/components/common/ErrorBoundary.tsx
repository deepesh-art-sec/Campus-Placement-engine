import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "./Button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null, showDetails: false };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    console.error("Uncaught runtime error caught by ErrorBoundary:", error, errorInfo);
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-[380px] p-6 sm:p-8 bg-[#0d1527] border border-[#1e3258] rounded-3xl max-w-lg mx-auto my-8 text-center space-y-5 text-white shadow-2xl">
          <div className="w-14 h-14 rounded-2xl bg-rose-950/80 border border-rose-500/40 text-rose-400 flex items-center justify-center mx-auto shadow-lg shadow-rose-950/40">
            <AlertTriangle className="w-7 h-7" />
          </div>

          <div>
            <h3 className="text-lg font-black text-white tracking-tight">Something Went Wrong</h3>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              A UI rendering error occurred. All your local placement data remains completely safe on this machine.
            </p>
          </div>

          {this.state.error && (
            <div className="text-left bg-[#080e1c] border border-[#1b2b4d] rounded-2xl p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono text-rose-400 font-bold truncate">
                  {this.state.error.message || "Unknown error"}
                </span>
                <button
                  type="button"
                  onClick={() => this.setState({ showDetails: !this.state.showDetails })}
                  className="text-[10px] text-cyan-400 hover:underline"
                >
                  {this.state.showDetails ? "Hide Stack" : "Show Stack"}
                </button>
              </div>

              {this.state.showDetails && this.state.errorInfo && (
                <pre className="text-[10px] font-mono text-slate-400 max-h-40 overflow-y-auto whitespace-pre-wrap">
                  {this.state.errorInfo.componentStack}
                </pre>
              )}
            </div>
          )}

          <div className="flex items-center justify-center gap-3 pt-2">
            <Button variant="secondary" size="sm" onClick={this.handleReset}>
              Try Again
            </Button>
            <Button
              variant="emerald"
              size="sm"
              icon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={this.handleReload}
            >
              Reload Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
