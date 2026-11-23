import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { vi } from "vitest";
import { SearchAutocomplete } from "./SearchAutocomplete";
import { loadSuggestions } from "./searchSuggestions";

vi.mock("./searchSuggestions", () => ({ loadSuggestions: vi.fn() }));
afterEach(() => vi.resetAllMocks());

test("debounces requests and passes the selected dataset and credentials", async () => {
  vi.mocked(loadSuggestions).mockResolvedValue([
    { text: "Khách sạn Hà Nội", label: "Trong thư viện" },
  ]);
  render(
    <SearchAutocomplete
      value="khach san"
      onChange={vi.fn()}
      disabled={false}
      token="token"
      sourceDataset="catalog"
    />,
  );
  fireEvent.focus(screen.getByRole("combobox"));
  expect(loadSuggestions).not.toHaveBeenCalled();
  expect(await screen.findByRole("option")).toHaveTextContent(
    "Khách sạn Hà Nội",
  );
  expect(loadSuggestions).toHaveBeenCalledWith(
    "khach san",
    expect.any(AbortSignal),
    "token",
    "catalog",
  );
});

test("a late response cannot replace suggestions for newer input", async () => {
  let resolveOld!: (items: { text: string; label: string }[]) => void;
  vi.mocked(loadSuggestions)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    )
    .mockResolvedValueOnce([{ text: "Đà Nẵng", label: "Trong thư viện" }]);
  const props = { onChange: vi.fn(), disabled: false };
  const { rerender } = render(<SearchAutocomplete {...props} value="ha noi" />);
  fireEvent.focus(screen.getByRole("combobox"));
  await waitFor(() => expect(loadSuggestions).toHaveBeenCalledOnce());
  const signal = vi.mocked(loadSuggestions).mock.calls[0][1];
  rerender(<SearchAutocomplete {...props} value="da nang" />);
  expect(signal.aborted).toBe(true);
  expect(await screen.findByRole("option")).toHaveTextContent("Đà Nẵng");
  await act(async () =>
    resolveOld([{ text: "Hà Nội", label: "Trong thư viện" }]),
  );
  expect(screen.getByRole("option")).toHaveTextContent("Đà Nẵng");
});

test("unavailable suggestions do not prevent typing or submitting search", async () => {
  vi.mocked(loadSuggestions).mockRejectedValue(new Error("offline"));
  const submit = vi.fn((e) => e.preventDefault());
  render(
    <form onSubmit={submit}>
      <SearchAutocomplete value="ha noi" onChange={vi.fn()} disabled={false} />
    </form>,
  );
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  await waitFor(() => expect(loadSuggestions).toHaveBeenCalledOnce());
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  fireEvent.keyDown(input, { key: "Enter" });
  expect(submit).toHaveBeenCalledOnce();
});
