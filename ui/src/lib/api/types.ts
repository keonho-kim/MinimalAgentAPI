export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type FsListItem = {
  name: string;
  path: string;
  type: "file" | "directory";
  size: number | null;
  modified_at: number;
};

export type FsListResponse = {
  path: string;
  files: FsListItem[];
};

export type FsMutationResponse = {
  path: string;
};

export type FsSearchResponse = {
  matches: FsListItem[];
};

export type SkillListItem = {
  name: string;
  description: string;
  path: string;
};

export type SkillSearchResponse = {
  matches: SkillListItem[];
};

export type PreviewType =
  | "pdf"
  | "office_pdf"
  | "xlsx_grid"
  | "hwpx"
  | "markdown"
  | "text"
  | "code";

export type XlsxCell = {
  address: string;
  row: number;
  column: number;
  value: string | number | boolean | null;
  formula: string | null;
  style: {
    bold?: boolean;
    italic?: boolean;
    horizontal?: string | null;
    vertical?: string | null;
    color?: string;
    background?: string;
  };
};

export type XlsxSheet = {
  id: string;
  name: string;
  visible: boolean;
  index: number;
  used_range: string;
  row_count: number;
  column_count: number;
  columns: Array<{ index: number; label: string; width: number }>;
  rows: Array<{ index: number; height: number }>;
  merged_ranges: string[];
  cells: XlsxCell[];
};

export type XlsxWorkbook = {
  sheet_count: number;
  sheets: XlsxSheet[];
};

export type PptxShapeBounds = {
  left: number;
  top: number;
  width: number;
  height: number;
};

export type PptxManualOverrides = {
  position: boolean;
  size: boolean;
  content: boolean;
  style: boolean;
};

export type PptxElementStyle = {
  fontFamily?: string | null;
  fontSize?: number | null;
  fontWeight?: number | null;
  color?: string | null;
  textAlign?: string | null;
  fillColor?: string | null;
  lineColor?: string | null;
};

export type PptxElementType =
  | "text"
  | "image"
  | "shape"
  | "line"
  | "group"
  | "table"
  | "chart"
  | "htmlEmbed";

export type PptxElement = {
  id: string;
  slideId: string;
  type: PptxElementType;
  role: string;
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  zIndex: number;
  pptxShapeId: number | null;
  style: PptxElementStyle;
  manualOverrides: PptxManualOverrides;
};

export type PptxSlide = {
  id: string;
  deckId: string;
  index: number;
  title: string;
  layoutType: string;
  background: Record<string, string>;
  elements: PptxElement[];
  notes: string;
  source: Record<string, string>;
  contentHash: string;
  layoutHash: string;
  visualHash: string;
  summaryHash: string;
};

export type PptxDeck = {
  id: string;
  title: string;
  sourceType: string;
  revision: number;
  canvas: {
    width: number;
    height: number;
  };
  slides: PptxSlide[];
};

export type PptxDeckResponse = {
  path: string;
  filename: string;
  source_url: string | null;
  readiness: {
    status: "ready" | "partial" | "failed";
    message: string;
  };
  deck: PptxDeck;
};

export type PptxOperation =
  | {
      type: "updateText";
      slideId: string;
      elementId: string;
      content: string;
    }
  | {
      type: "moveElement";
      slideId: string;
      elementId: string;
      x: number;
      y: number;
    }
  | {
      type: "resizeElement";
      slideId: string;
      elementId: string;
      width: number;
      height: number;
    }
  | {
      type: "updateStyle";
      slideId: string;
      elementId: string;
      style: PptxElementStyle;
    }
  | {
      type: "addElement";
      slideId: string;
      element: PptxElement;
    }
  | {
      type: "deleteElement";
      slideId: string;
      elementId: string;
    }
  | {
      type: "applyLayout";
      slideId: string;
      layoutId: string;
      respectManualOverrides: boolean;
    }
  | {
      type: "reorderSlides";
      slideIdOrder: string[];
    }
  | {
      type: "createSlide";
      afterSlideId?: string;
      templateId?: string;
      contentMap?: Record<string, unknown>;
    }
  | {
      type: "deleteSlide";
      slideId: string;
    };

export type PptxOperationResponse = {
  path: string;
  revision: number;
  changed_slide_ids: string[];
  rejected_operations: Array<Record<string, unknown>>;
  deck: PptxDeck;
};

export type PptxSearchResponse = {
  matches: Array<{
    slideId: string;
    slideIndex: number;
    title: string;
    snippet: string;
  }>;
};

export type PptxExportResponse = {
  file_id: string;
  filename: string;
  download_url: string;
  job_id: string;
};

export type FsPreviewResponse = {
  path: string;
  filename: string;
  file_type: string;
  preview_type: PreviewType;
  source_url: string | null;
  workbook: XlsxWorkbook | null;
  presentation: PptxDeck | null;
};

export type HitlActionRequest = {
  name: string;
  args: Record<string, unknown>;
  description?: string | null;
  allowed_decisions: Array<"approve" | "edit" | "reject">;
};

export type HitlRequest = {
  stream_id: string;
  actions: HitlActionRequest[];
  approval_scope?: string | null;
};

export type HitlApprovalScope = "once" | "agent" | "core";

export type HitlDecision =
  | { type: "approve" }
  | {
      type: "edit";
      edited_action: {
        name: string;
        args: Record<string, unknown>;
      };
    }
  | { type: "reject"; message?: string };

export type UploadedFileResponse = {
  file_id: string;
  filename: string;
  file_type: string;
  status: "uploaded" | "converted" | "conversion_failed";
  path: string | null;
  error: string | null;
};

export type UploadResponse = {
  uploaded_files: UploadedFileResponse[];
};
