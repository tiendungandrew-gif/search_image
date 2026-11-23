import { Component, type PropsWithChildren } from "react";

export class ErrorBoundary extends Component<
  PropsWithChildren,
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed)
      return (
        <main className="app-shell empty-results" role="alert">
          <h1>Giao diện tạm thời chưa hiển thị được.</h1>
          <p>Tải lại trang để mở lại ứng dụng.</p>
          <button type="button" onClick={() => window.location.reload()}>
            Tải lại giao diện
          </button>
        </main>
      );
    return this.props.children;
  }
}
