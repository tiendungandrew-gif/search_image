import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ImageUpload } from "./ImageUpload";

test("drop rejects multiple files and accepts a valid query image without a request", () => {
  const onChange = vi.fn();
  const fetch = vi.fn();
  vi.stubGlobal("fetch", fetch);
  render(<ImageUpload file={null} onChange={onChange} />);
  const file = new File(["local-test"], "photo.webp", { type: "image/webp" });
  const target = screen.getByLabelText("Thêm ảnh tham chiếu").closest("label")!;
  fireEvent.drop(target, { dataTransfer: { files: [file, file] } });
  expect(screen.getByRole("alert")).toHaveTextContent("đúng một");
  fireEvent.drop(target, { dataTransfer: { files: [file] } });
  expect(onChange).toHaveBeenCalledWith(file);
  expect(fetch).not.toHaveBeenCalled();
});
test("preview URLs are revoked on replacement and unmount", () => {
  const first = new File(["one"], "1.png", { type: "image/png" });
  const second = new File(["two"], "2.png", { type: "image/png" });
  const { rerender, unmount } = render(
    <ImageUpload file={first} onChange={vi.fn()} />,
  );
  const revocations = vi.mocked(URL.revokeObjectURL).mock.calls.length;
  rerender(<ImageUpload file={second} onChange={vi.fn()} />);
  expect(URL.revokeObjectURL).toHaveBeenCalledTimes(revocations + 1);
  unmount();
  expect(URL.revokeObjectURL).toHaveBeenCalledTimes(revocations + 2);
});
