import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { authAPI } from "./api";
import { LoginPage } from "./LoginPage";

const password = "Registration-test-only-2026!";
async function openSignup() {
  render(
    <LoginPage
      login={vi.fn()}
      error={null}
      retry={vi.fn()}
      operatorEnabled={false}
    />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Đăng ký" }));
  await user.type(screen.getByLabelText("Tên hiển thị"), "  Người dùng  ");
  await user.type(screen.getByLabelText("Tên đăng nhập"), "New_Reader");
  await user.type(screen.getByLabelText("Mật khẩu", { exact: true }), password);
  return user;
}

test("mismatched confirmation stays on signup without creating an account", async () => {
  const register = vi.spyOn(authAPI, "register");
  const user = await openSignup();
  await user.type(
    screen.getByLabelText("Xác nhận mật khẩu"),
    "another-long-password",
  );
  await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));
  expect(screen.getByRole("alert")).toHaveTextContent("chưa khớp");
  expect(screen.getByLabelText("Xác nhận mật khẩu")).toHaveFocus();
  expect(register).not.toHaveBeenCalled();
});

test("successful signup normalizes username and returns to login without passwords", async () => {
  const register = vi.spyOn(authAPI, "register").mockResolvedValue(undefined);
  const user = await openSignup();
  await user.type(screen.getByLabelText("Xác nhận mật khẩu"), password);
  await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));
  expect(register).toHaveBeenCalledWith("Người dùng", "new_reader", password);
  expect(
    await screen.findByRole("heading", { name: "Đăng nhập vào Synlens" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent(
    "Tạo tài khoản thành công",
  );
  expect(screen.getByLabelText("Tên đăng nhập")).toHaveValue("new_reader");
  expect(screen.getByLabelText("Mật khẩu", { exact: true })).toHaveValue("");
});

test("server error keeps form values for retry and pending signup blocks repeat submission", async () => {
  let reject!: (reason: Error) => void;
  const register = vi.spyOn(authAPI, "register").mockImplementation(
    () =>
      new Promise((_resolve, fail) => {
        reject = fail;
      }),
  );
  const user = await openSignup();
  await user.type(screen.getByLabelText("Xác nhận mật khẩu"), password);
  await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));
  expect(
    screen.getByRole("button", { name: "Đang tạo tài khoản…" }),
  ).toBeDisabled();
  expect(screen.getByRole("button", { name: "Đăng nhập" })).toBeDisabled();
  expect(register).toHaveBeenCalledTimes(1);
  reject(new Error("Tên đăng nhập này không khả dụng"));
  expect(await screen.findByRole("alert")).toHaveTextContent("không khả dụng");
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Tạo tài khoản" })).toBeEnabled(),
  );
  expect(screen.getByLabelText("Tên đăng nhập")).toHaveValue("New_Reader");
});
