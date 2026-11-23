import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { adminAPI } from "./api";
import { DatasetsPanel } from "./DatasetsPanel";
import { UsersPanel } from "./UsersPanel";
import type { CatalogDataset } from "../../types/access";

const common: CatalogDataset = {
  id: "12345678-1234-4234-8234-123456789001",
  key: "common",
  name: "Thư viện chung QA",
  description: "",
  is_active: true,
  shared_with_members: true,
  images: 2,
};
const privateLibrary: CatalogDataset = {
  ...common,
  id: "12345678-1234-4234-8234-123456789002",
  key: "private",
  name: "Thư viện riêng QA",
  shared_with_members: false,
};
const uid = "12345678-1234-4234-8234-123456789003";
function mockDatasets() {
  vi.spyOn(adminAPI, "datasets").mockResolvedValue([common, privateLibrary]);
  vi.spyOn(adminAPI, "images").mockResolvedValue({ rows: [], total: 0 });
}

test("public guest access is separate from member sharing and defaults off", async () => {
  mockDatasets();
  const update = vi
    .spyOn(adminAPI, "updateDataset")
    .mockResolvedValue({ status: "updated" });
  render(<DatasetsPanel />);
  const user = userEvent.setup();
  const title = await screen.findByText(privateLibrary.name, {
    selector: "strong",
  });
  const tile = title.closest("details")!;
  await user.click(tile.querySelector("summary")!);
  const form = within(tile);
  const checkbox = form.getByRole("checkbox", {
    name: "Công khai cho khách (không cần đăng nhập)",
  });
  expect(checkbox).not.toBeChecked();
  await user.click(checkbox);
  await user.click(form.getByRole("button", { name: "Lưu thư viện" }));
  expect(update).toHaveBeenCalledWith(
    privateLibrary.id,
    expect.objectContaining({ is_public: true, shared_with_members: false }),
  );
});

test("sharing is an explicit Admin choice and new library defaults to private", async () => {
  mockDatasets();
  const update = vi
    .spyOn(adminAPI, "updateDataset")
    .mockResolvedValue({ status: "updated" });
  render(<DatasetsPanel />);
  const user = userEvent.setup();
  const title = await screen.findByText(privateLibrary.name, {
    selector: "strong",
  });
  const tile = title.closest("details")!;
  await user.click(tile.querySelector("summary")!);
  const form = within(tile);
  const shared = form.getByRole("checkbox", {
    name: "Chia sẻ cho mọi thành viên",
  });
  expect(shared).not.toBeChecked();
  await user.click(shared);
  await user.click(form.getByRole("button", { name: "Lưu thư viện" }));
  expect(update).toHaveBeenCalledWith(
    privateLibrary.id,
    expect.objectContaining({ shared_with_members: true, is_active: true }),
  );
  const create = screen
    .getByText("Tạo thư viện", { selector: "summary" })
    .closest("details")!;
  await user.click(create.querySelector("summary")!);
  expect(
    within(create).getByRole("checkbox", {
      name: "Chia sẻ cho mọi thành viên",
    }),
  ).not.toBeChecked();
});

test("common access is displayed automatically while only private grants are saved", async () => {
  mockDatasets();
  vi.spyOn(adminAPI, "users").mockResolvedValue({
    rows: [
      {
        id: uid,
        username: "reader",
        display_name: "QA Reader",
        role: "user",
        is_active: true,
        dataset_ids: [],
      },
    ],
    total: 1,
  });
  const grants = vi
    .spyOn(adminAPI, "grants")
    .mockResolvedValue({ status: "updated" });
  const revoke = vi
    .spyOn(adminAPI, "revokeSessions")
    .mockResolvedValue({ status: "sessions_revoked" });
  render(<UsersPanel />);
  const user = userEvent.setup();
  const tile = (
    await screen.findByText("QA Reader", { selector: "strong" })
  ).closest("details")!;
  await user.click(tile.querySelector("summary")!);
  const form = within(tile);
  const automatic = form.getByRole("checkbox", { name: /Thư viện chung QA/ });
  expect(automatic).toBeChecked();
  expect(automatic).toBeDisabled();
  const assigned = form.getByRole("checkbox", { name: privateLibrary.name });
  expect(assigned).not.toBeChecked();
  expect(assigned).toBeEnabled();
  await user.click(assigned);
  await user.click(form.getByRole("button", { name: "Lưu quyền thư viện" }));
  expect(grants).toHaveBeenCalledWith(uid, [privateLibrary.id]);
  await screen.findByText("Đã cập nhật quyền thư viện.");
  await user.click(
    form.getByRole("button", { name: "Đăng xuất mọi thiết bị" }),
  );
  expect(revoke).toHaveBeenCalledWith(uid);
});
