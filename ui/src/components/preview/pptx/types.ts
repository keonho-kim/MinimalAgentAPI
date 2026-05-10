import type { PDFDocumentProxy } from "pdfjs-dist";

import type { PptxElement } from "@/lib/api";

export type PdfDocument = PDFDocumentProxy;

export type SlideViewport = {
  width: number;
  height: number;
};

export type PptxTextShapeDraft = {
  element: PptxElement;
  text: string;
  x: number;
  y: number;
  width: number;
  height: number;
};
