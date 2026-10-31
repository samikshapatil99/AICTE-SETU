import React from "react";
export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { err: any }> {
  constructor(p: any) { super(p); this.state = { err: null }; }
  static getDerivedStateFromError(err: any) { return { err }; }
  componentDidCatch(err: any) { console.error(err); }
  render() {
    if (this.state.err) {
      return (
        <div className="p-6">
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-md p-4">
            <div className="font-semibold">Something went wrong.</div>
            <div className="text-sm mt-1">{String(this.state.err?.message || this.state.err)}</div>
            <button className="mt-3 text-sm underline" onClick={() => this.setState({ err: null })}>Try again</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}