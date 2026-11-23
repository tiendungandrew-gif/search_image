import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { LoginPage } from "./LoginPage";
import { decodeAuth } from "./api";
const props = () => ({
  login: vi.fn().mockResolvedValue(undefined),
  error: null,
  retry: vi.fn(),
  operatorEnabled: false,
  quickLogin: vi.fn().mockResolvedValue(undefined),
});
test("quick sign-in controls stay absent unless the backend advertises ready roles", () => {
  render(<LoginPage {...props()} />);
  expect(
    screen.queryByRole("button", { name: /Vào nhanh/ }),
  ).not.toBeInTheDocument();
});
test.each(["admin", "user"] as const)(
  "quick %s uses the role endpoint without a password",
  async (role) => {
    const handlers = props();
    render(<LoginPage {...handlers} quickRoles={["admin", "user"]} />);
    await userEvent.click(
      screen.getByRole("button", {
        name: new RegExp(
          role === "admin" ? "Vào nhanh Admin" : "Vào nhanh User",
        ),
      }),
    );
    expect(handlers.quickLogin).toHaveBeenCalledWith(role);
    expect(handlers.login).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Mật khẩu", { exact: true })).toHaveValue("");
  },
);
test("pending quick sign-in disables both roles and an error permits retry", async () => {
  const handlers = props();
  let reject!: (error: Error) => void;
  handlers.quickLogin.mockImplementationOnce(
    () =>
      new Promise<void>((_, fail) => {
        reject = fail;
      }),
  );
  render(<LoginPage {...handlers} quickRoles={["admin", "user"]} />);
  await userEvent.click(
    screen.getByRole("button", { name: /Vào nhanh Admin/ }),
  );
  expect(screen.getByRole("button", { name: /Vào nhanh User/ })).toBeDisabled();
  reject(new Error("Tài khoản trải nghiệm chưa sẵn sàng"));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Tài khoản trải nghiệm chưa sẵn sàng",
  );
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: /Vào nhanh User/ }),
    ).toBeEnabled(),
  );
  await userEvent.click(screen.getByRole("button", { name: /Vào nhanh User/ }));
  expect(handlers.quickLogin).toHaveBeenLastCalledWith("user");
});
test("ordinary username/password login remains available next to quick roles", async () => {
  const handlers = props();
  render(<LoginPage {...handlers} quickRoles={["admin", "user"]} />);
  const user = userEvent.setup();
  await user.type(
    screen.getByLabelText("Tên đăng nhập", { exact: true }),
    "My_Admin",
  );
  await user.type(
    screen.getByLabelText("Mật khẩu", { exact: true }),
    "ordinary-test-password",
  );
  await user.click(screen.getByRole("button", { name: /^Đăng nhập$/ }));
  expect(handlers.login).toHaveBeenCalledWith(
    "my_admin",
    "ordinary-test-password",
  );
  expect(handlers.quickLogin).not.toHaveBeenCalled();
});
test("auth decoder validates advertised roles and accepts older account snapshots", () => {
  expect(
    decodeAuth({ user: null, legacy_enabled: false }).quick_login_roles,
  ).toEqual([]);
  for (const roles of [["owner"], ["admin", "admin"], "admin", null]) {
    expect(() =>
      decodeAuth({
        user: null,
        legacy_enabled: false,
        quick_login_roles: roles,
      }),
    ).toThrow();
  }
});

test("password visibility is explicit and does not submit or change the password", async () => {
  const handlers = props();
  render(<LoginPage {...handlers} />);
  const user = userEvent.setup();
  const password = screen.getByLabelText("Mật khẩu", { exact: true });
  await user.type(password, "example-password");
  expect(password).toHaveAttribute("type", "password");
  await user.click(screen.getByRole("button", { name: "Hiện mật khẩu" }));
  expect(password).toHaveAttribute("type", "text");
  expect(password).toHaveValue("example-password");
  await user.click(screen.getByRole("button", { name: "Ẩn mật khẩu" }));
  expect(password).toHaveAttribute("type", "password");
  expect(handlers.login).not.toHaveBeenCalled();
});
