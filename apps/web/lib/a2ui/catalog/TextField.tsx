"use client";

import { CatalogComponentProps } from "../Renderer";
import { resolveValue } from "../resolve";
import { isBinding } from "../types";

export function TextFieldComp({ node, ctx }: CatalogComponentProps) {
  const label = resolveValue(node.label, ctx.state.dataModel, ctx.scope);
  const valueRaw = resolveValue(node.value, ctx.state.dataModel, ctx.scope);
  const value = valueRaw == null ? "" : String(valueRaw);
  const fieldType = typeof node.textFieldType === "string" ? node.textFieldType : "text";

  // Resolve the absolute writeback path from the value binding.
  const binding = node.value;
  const writePath = isBinding(binding)
    ? binding.path.startsWith("/")
      ? binding.path
      : `${ctx.scope}/${binding.path}`
    : null;

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (writePath) ctx.onDataModelChange(writePath, e.target.value);
  }

  return (
    <label className="a2-field">
      {typeof label === "string" && label !== "" ? (
        <span className="a2-field__label">{label}</span>
      ) : null}
      <span className="a2-field__shell">
        <input
          className="a2-field__input"
          type={fieldType === "password" ? "password" : "text"}
          value={value}
          onChange={handleChange}
          disabled={writePath === null}
          spellCheck={false}
        />
        <span className="a2-field__rule" aria-hidden />
      </span>
    </label>
  );
}
