import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

import { ErrorState, Field, Notice } from "./ui";

describe("shared UI", () => {
  it("connects a field's label, help and error to its input", () => {
    render(<Field label="Email" help="We never share this." error="Please check this.">{(props) => <input {...props} />}</Field>);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input.getAttribute("aria-describedby")).toContain("-help");
    expect(input.getAttribute("aria-describedby")).toContain("-error");
  });
  it("announces error notices and does not rely on colour alone", () => {
    render(<Notice tone="danger" title="That did not work" />);
    expect(screen.getByRole("alert")).toHaveTextContent("That did not work");
  });
  it("shows the server's message and offers a retry", async () => {
    const retry = vi.fn();
    render(<ErrorState error={new ApiError(500, "x", "Something went wrong on our side.")} onRetry={retry} what="This page" />);
    expect(screen.getByRole("alert")).toHaveTextContent("on our side");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });
});
