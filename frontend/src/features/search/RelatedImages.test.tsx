import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { vi } from "vitest";
import { api } from "../../services/api/client";
import type { SearchResponse, SearchResult } from "../../types/api";
import { RelatedImages } from "./RelatedImages";
vi.mock("../../services/api/client", () => ({
  api: { relatedImages: vi.fn() },
}));
vi.mock("./ResultImage", () => ({
  ResultImage: ({
    onOpen,
    actionLabel,
  }: {
    onOpen: () => void;
    actionLabel: string;
  }) => <button onClick={onOpen}>{actionLabel}</button>,
}));
const image = (id: string): SearchResult =>
  ({
    image_id: id,
    rank: 1,
    score: 0.8,
    score_type: "cosine",
    ranking_version: "cosine-v1",
    image_url: "/image",
    thumbnail_url: "/thumbnail",
    constraint_assessments: [],
    metadata: {
      title: id,
      width: 600,
      height: 400,
      media_type: "image/jpeg",
      tags: [],
      source_dataset: "public",
      city: null,
      license: null,
    },
  }) as SearchResult;
const response = (...ids: string[]) =>
  ({ results: ids.map(image) }) as SearchResponse;
afterEach(() => vi.resetAllMocks());

test("shows related images, excludes reference and supports drilling into another image", async () => {
  vi.mocked(api.relatedImages).mockResolvedValue(
    response("reference", "beach"),
  );
  const select = vi.fn();
  render(
    <RelatedImages imageId="reference" token="member" onSelect={select} />,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Xem ảnh liên quan: beach" }),
  );
  expect(select).toHaveBeenCalledWith(
    expect.objectContaining({ image_id: "beach" }),
  );
  expect(
    screen.queryByRole("button", { name: "reference" }),
  ).not.toBeInTheDocument();
  expect(api.relatedImages).toHaveBeenCalledWith(
    "reference",
    "member",
    expect.any(AbortSignal),
  );
});

test("changing reference aborts the previous request and ignores its late response", async () => {
  let resolveOld!: (value: SearchResponse) => void;
  vi.mocked(api.relatedImages)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        }),
    )
    .mockResolvedValueOnce(response("new-match"));
  const props = { token: "", onSelect: vi.fn() };
  const { rerender } = render(<RelatedImages {...props} imageId="old" />);
  const signal = vi.mocked(api.relatedImages).mock.calls[0][2];
  rerender(<RelatedImages {...props} imageId="new" />);
  expect(signal?.aborted).toBe(true);
  await screen.findByRole("button", { name: "new-match" });
  await act(async () => resolveOld(response("stale")));
  expect(
    screen.queryByRole("button", { name: "stale" }),
  ).not.toBeInTheDocument();
});

test("failed recommendations can be retried without closing the image", async () => {
  vi.mocked(api.relatedImages)
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(response());
  render(<RelatedImages imageId="reference" token="" onSelect={vi.fn()} />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Tải lại ảnh cùng chủ đề" }),
  );
  await waitFor(() =>
    expect(screen.getByText(/Chưa có ảnh liên quan/)).toBeVisible(),
  );
  expect(api.relatedImages).toHaveBeenCalledTimes(2);
});
