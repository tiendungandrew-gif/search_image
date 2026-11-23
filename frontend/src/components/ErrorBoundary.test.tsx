import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

test("render errors have a recoverable fallback without exposing exception details", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  function Broken(): never {
    throw new Error("private-fixture-detail");
  }
  render(
    <ErrorBoundary>
      <Broken />
    </ErrorBoundary>,
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Giao diện tạm thời");
  expect(
    screen.getByRole("button", { name: "Tải lại giao diện" }),
  ).toBeEnabled();
  expect(screen.queryByText(/private-fixture-detail/)).not.toBeInTheDocument();
});

test("healthy children remain functional", () => {
  render(
    <ErrorBoundary>
      <button>Search fixture</button>
    </ErrorBoundary>,
  );
  expect(screen.getByRole("button", { name: "Search fixture" })).toBeEnabled();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
