"use client";

import { CatalogComponentProps } from "../Renderer";
import { isTemplateChildren } from "../types";
import { getAtPointer } from "../pointer";

export function List({ node, ctx }: CatalogComponentProps) {
  const children = node.children;
  if (!isTemplateChildren(children)) {
    return <div className="a2-list a2-list--empty" />;
  }
  const arrPath = children.path;
  const componentId = children.componentId;
  const arr = getAtPointer(ctx.state.dataModel, arrPath);
  const items = Array.isArray(arr) ? arr : [];

  return (
    <div className="a2-list">
      {items.map((_, i) => {
        // Bindings inside the template are RELATIVE to the array item.
        const itemScope = `${arrPath}/${i}`;
        return (
          <div className="a2-list__item" key={itemScope}>
            {ctx.render(componentId, itemScope)}
          </div>
        );
      })}
    </div>
  );
}
