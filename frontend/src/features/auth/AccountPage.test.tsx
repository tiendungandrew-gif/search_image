import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import AccountPage from "./AccountPage";
import { authAPI } from "./api";
const account = {
  id: "reader",
  username: "reader",
  display_name: "Reader",
  role: "user" as const,
  is_active: true,
  datasets: [],
};

async function fill(
  current: string,
  password: string,
  confirmation = password,
) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Mật khẩu hiện tại"), current);
  await user.type(
    screen.getByLabelText("Mật khẩu mới", { exact: true }),
    password,
  );
  await user.type(screen.getByLabelText("Nhập lại mật khẩu mới"), confirmation);
  await user.click(screen.getByRole("button", { name: "Lưu mật khẩu" }));
}

afterEach(() => vi.restoreAllMocks());
test("rejects mismatched confirmation without calling API", async () => {
  const save = vi.spyOn(authAPI, "password").mockResolvedValue(undefined);
  render(<AccountPage user={account} onChanged={vi.fn()} />);
  await fill("old-password-123", "new-password-123", "other-password-123");
  expect(screen.getByRole("alert")).toHaveTextContent("chưa khớp");
  expect(save).not.toHaveBeenCalled();
});
test("rejects reuse of current password", async () => {
  const save = vi.spyOn(authAPI, "password").mockResolvedValue(undefined);
  render(<AccountPage user={account} onChanged={vi.fn()} />);
  await fill("old-password-123", "old-password-123");
  expect(screen.getByRole("alert")).toHaveTextContent("phải khác");
  expect(save).not.toHaveBeenCalled();
});
test("submits password and clears secrets after success", async () => {
  const save = vi.spyOn(authAPI, "password").mockResolvedValue(undefined);
  const changed = vi.fn();
  render(<AccountPage user={account} onChanged={changed} />);
  await fill("old-password-123", "new-password-123");
  expect(save).toHaveBeenCalledWith("old-password-123", "new-password-123");
  expect(changed).toHaveBeenCalledOnce();
  expect(screen.getByLabelText("Mật khẩu hiện tại")).toHaveValue("");
});
test("shows server errors and permits retry", async () => {
  vi.spyOn(authAPI, "password").mockRejectedValue(
    new Error("Mật khẩu hiện tại không đúng"),
  );
  const changed = vi.fn();
  render(<AccountPage user={account} onChanged={changed} />);
  await fill("old-password-123", "new-password-123");
  expect(await screen.findByRole("alert")).toHaveTextContent("không đúng");
  expect(screen.getByRole("button", { name: "Lưu mật khẩu" })).toBeEnabled();
  expect(changed).not.toHaveBeenCalled();
});
