"use client";

import { FC } from "react";
import type { CatalogComponentProps } from "../Renderer";
import { Column } from "./Column";
import { Row } from "./Row";
import { List } from "./List";
import { TextComp } from "./Text";
import { ImageComp } from "./Image";
import { IconComp } from "./Icon";
import { DividerComp } from "./Divider";
import { ButtonComp } from "./Button";
import { TextFieldComp } from "./TextField";
import { CardComp } from "./Card";

export const CATALOG: Record<string, FC<CatalogComponentProps>> = {
  Column,
  Row,
  List,
  Text: TextComp,
  Image: ImageComp,
  Icon: IconComp,
  Divider: DividerComp,
  Button: ButtonComp,
  TextField: TextFieldComp,
  Card: CardComp,
};
