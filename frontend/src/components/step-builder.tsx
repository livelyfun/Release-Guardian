"use client";

import type { BrowserStep, BrowserStepAction } from "@/lib/types";

const ACTIONS: { value: BrowserStepAction; label: string }[] = [
  { value: "goto", label: "Go to URL" },
  { value: "click", label: "Click" },
  { value: "fill", label: "Fill field" },
  { value: "select", label: "Select option" },
  { value: "press", label: "Press key" },
  { value: "expect_text", label: "Expect text" },
  { value: "expect_visible", label: "Expect visible" },
  { value: "expect_url", label: "Expect URL contains" },
  { value: "wait", label: "Wait (ms)" },
  { value: "screenshot", label: "Screenshot" },
];

export function newBrowserStep(action: BrowserStepAction = "goto"): BrowserStep {
  return { action };
}

export function StepBuilder({
  steps,
  onChange,
  disabled = false,
}: {
  steps: BrowserStep[];
  onChange: (steps: BrowserStep[]) => void;
  disabled?: boolean;
}) {
  function update(index: number, patch: Partial<BrowserStep>) {
    onChange(steps.map((step, position) => (position === index ? { ...step, ...patch } : step)));
  }

  function changeAction(index: number, action: BrowserStepAction) {
    onChange(steps.map((step, position) => (position === index ? { action } : step)));
  }

  function remove(index: number) {
    onChange(steps.filter((_, position) => position !== index));
  }

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= steps.length) return;
    const next = [...steps];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">Browser journey steps</p>
          <p className="text-xs text-slate-500">
            Each step runs in order against the target URL. Keep the first step as a
            navigation.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary text-xs"
          disabled={disabled}
          onClick={() => onChange([...steps, newBrowserStep("click")])}
        >
          Add step
        </button>
      </div>

      {steps.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 px-3 py-4 text-sm text-slate-500">
          No steps yet. Add a “Go to URL” step to start the journey.
        </p>
      ) : (
        <ol className="space-y-2">
          {steps.map((step, index) => (
            <li
              key={`${index}-${step.action}`}
              className="rounded-lg border border-slate-200 bg-white p-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="w-6 text-xs font-medium text-slate-500">{index + 1}</span>
                <select
                  aria-label={`Action for step ${index + 1}`}
                  className="input w-auto py-1 text-xs"
                  value={step.action}
                  disabled={disabled}
                  onChange={(event) =>
                    changeAction(index, event.target.value as BrowserStepAction)
                  }
                >
                  {ACTIONS.map((action) => (
                    <option key={action.value} value={action.value}>
                      {action.label}
                    </option>
                  ))}
                </select>

                <div className="flex flex-1 flex-wrap items-center gap-2">
                  {step.action === "goto" ? (
                    <input
                      aria-label={`URL for step ${index + 1}`}
                      className="input min-w-48 flex-1 py-1 text-xs"
                      value={step.url ?? ""}
                      placeholder="/pricing"
                      disabled={disabled}
                      onChange={(event) => update(index, { url: event.target.value })}
                    />
                  ) : null}

                  {["click", "fill", "select", "press", "expect_visible"].includes(
                    step.action,
                  ) ? (
                    <input
                      aria-label={`Selector for step ${index + 1}`}
                      className="input min-w-40 flex-1 py-1 text-xs"
                      value={step.selector ?? ""}
                      placeholder="#submit or text=Sign in"
                      disabled={disabled}
                      onChange={(event) => update(index, { selector: event.target.value })}
                    />
                  ) : null}

                  {["fill", "select"].includes(step.action) ? (
                    <input
                      aria-label={`Value for step ${index + 1}`}
                      className="input min-w-32 flex-1 py-1 text-xs"
                      value={step.value ?? ""}
                      placeholder="Value"
                      disabled={disabled}
                      onChange={(event) => update(index, { value: event.target.value })}
                    />
                  ) : null}

                  {step.action === "press" ? (
                    <input
                      aria-label={`Key for step ${index + 1}`}
                      className="input w-28 py-1 text-xs"
                      value={step.key ?? ""}
                      placeholder="Enter"
                      disabled={disabled}
                      onChange={(event) => update(index, { key: event.target.value })}
                    />
                  ) : null}

                  {step.action === "expect_text" ? (
                    <>
                      <input
                        aria-label={`Expected text for step ${index + 1}`}
                        className="input min-w-40 flex-1 py-1 text-xs"
                        value={step.text ?? ""}
                        placeholder="Welcome back"
                        disabled={disabled}
                        onChange={(event) => update(index, { text: event.target.value })}
                      />
                      <label className="flex items-center gap-1 text-xs text-slate-600">
                        <input
                          type="checkbox"
                          checked={Boolean(step.exact)}
                          disabled={disabled}
                          onChange={(event) => update(index, { exact: event.target.checked })}
                        />
                        Exact
                      </label>
                    </>
                  ) : null}

                  {step.action === "expect_url" ? (
                    <input
                      aria-label={`Expected URL fragment for step ${index + 1}`}
                      className="input min-w-40 flex-1 py-1 text-xs"
                      value={step.contains ?? ""}
                      placeholder="/dashboard"
                      disabled={disabled}
                      onChange={(event) => update(index, { contains: event.target.value })}
                    />
                  ) : null}

                  {step.action === "wait" ? (
                    <input
                      aria-label={`Wait milliseconds for step ${index + 1}`}
                      className="input w-28 py-1 text-xs"
                      type="number"
                      min={0}
                      value={step.ms ?? 1000}
                      disabled={disabled}
                      onChange={(event) =>
                        update(index, { ms: Number(event.target.value) })
                      }
                    />
                  ) : null}

                  {step.action === "screenshot" ? (
                    <label className="flex items-center gap-1 text-xs text-slate-600">
                      <input
                        type="checkbox"
                        checked={step.full_page ?? true}
                        disabled={disabled}
                        onChange={(event) =>
                          update(index, { full_page: event.target.checked })
                        }
                      />
                      Full page
                    </label>
                  ) : null}
                </div>

                <div className="flex items-center gap-1 text-xs">
                  <button
                    type="button"
                    className="px-1 text-slate-500 hover:text-slate-900 disabled:opacity-30"
                    aria-label={`Move step ${index + 1} up`}
                    disabled={disabled || index === 0}
                    onClick={() => move(index, -1)}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="px-1 text-slate-500 hover:text-slate-900 disabled:opacity-30"
                    aria-label={`Move step ${index + 1} down`}
                    disabled={disabled || index === steps.length - 1}
                    onClick={() => move(index, 1)}
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    className="px-1 text-red-600 hover:underline"
                    disabled={disabled}
                    onClick={() => remove(index)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
