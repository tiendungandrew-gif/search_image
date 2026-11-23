import { fireEvent, render, screen } from "@testing-library/react";
import { afterAll, afterEach, beforeEach, test, expect, vi } from "vitest";
import ImageDetailDialog from "./ImageDetailDialog";
import type { GalleryImage } from "./ResultGallery";

vi.mock("../../services/api/client", () => ({
  api: { imageDetail: () => new Promise(() => {}) },
}));
vi.mock("./ResultImage", () => ({ ResultImage: () => <div>Ảnh thử</div> }));

const showModal = HTMLDialogElement.prototype.showModal;
const close = HTMLDialogElement.prototype.close;
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
});
afterEach(() => vi.useRealTimers());
afterAll(() => {
  HTMLDialogElement.prototype.showModal = showModal;
  HTMLDialogElement.prototype.close = close;
});
const image: GalleryImage = {
  image_id: "image-1",
  rank: 1,
  score: null,
  score_type: null,
  image_url: "/image",
  thumbnail_url: "/thumbnail",
  metadata: {
    title: "Ảnh",
    caption: null,
    width: 640,
    height: 480,
    media_type: "image/jpeg",
    tags: [],
    source_dataset: "sample",
    city: null,
    license: null,
  },
};
function setup(reduced: boolean, consumer = true) {
  vi.stubGlobal("matchMedia", () => ({ matches: reduced }));
  const onClose = vi.fn();
  const view = render(
    <div className={consumer ? "consumer-site" : ""}>
      <ImageDetailDialog
        images={[image]}
        selected={0}
        token=""
        onSelect={vi.fn()}
        onClose={onClose}
      />
    </div>,
  );
  return { onClose, ...view };
}
test("animated close waits for exit and fires once", () => {
  vi.useFakeTimers();
  const { onClose } = setup(false);
  fireEvent.click(screen.getByRole("button", { name: "Đóng chi tiết ảnh" }));
  expect(screen.getByRole("dialog")).toHaveClass("is-closing");
  expect(onClose).not.toHaveBeenCalled();
  vi.advanceTimersByTime(170);
  expect(onClose).toHaveBeenCalledTimes(1);
});
test("reduced motion closes immediately", () => {
  const { onClose } = setup(true);
  fireEvent.click(screen.getByRole("button", { name: "Đóng chi tiết ảnh" }));
  expect(onClose).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("dialog")).not.toHaveClass("is-closing");
});
test("other workspaces close immediately", () => {
  const { onClose } = setup(false, false);
  fireEvent.click(screen.getByRole("button", { name: "Đóng chi tiết ảnh" }));
  expect(onClose).toHaveBeenCalledTimes(1);
});
test("leaving the page cancels a pending animated close", () => {
  vi.useFakeTimers();
  const { onClose, unmount } = setup(false);
  fireEvent.click(screen.getByRole("button", { name: "Đóng chi tiết ảnh" }));
  unmount();
  vi.runAllTimers();
  expect(onClose).not.toHaveBeenCalled();
});
