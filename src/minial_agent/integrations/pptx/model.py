from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


PptxElementType = Literal[
    "text",
    "image",
    "shape",
    "line",
    "group",
    "table",
    "chart",
    "htmlEmbed",
]
PptxOperationOrigin = Literal["user", "ai"]
PptxOperationType = Literal[
    "updateText",
    "updateStyle",
    "addElement",
    "deleteElement",
    "moveElement",
    "resizeElement",
    "applyLayout",
    "reorderSlides",
    "createSlide",
    "deleteSlide",
]


class PptxCanvas(BaseModel):
    width: int
    height: int


class PptxTheme(BaseModel):
    fontFamily: str = "Aptos"
    primaryColor: str = "#111827"
    accentColor: str = "#2563EB"
    backgroundColor: str = "#FFFFFF"


class PptxManualOverrides(BaseModel):
    position: bool = False
    size: bool = False
    content: bool = False
    style: bool = False


class PptxElementStyle(BaseModel):
    fontFamily: str | None = None
    fontSize: float | None = None
    fontWeight: int | None = None
    color: str | None = None
    textAlign: str | None = None
    fillColor: str | None = None
    lineColor: str | None = None


class PptxElement(BaseModel):
    id: str
    slideId: str
    type: PptxElementType
    role: str = "body"
    content: str = ""
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    rotation: float = 0
    zIndex: int = 0
    pptxShapeId: int | None = None
    style: PptxElementStyle = Field(default_factory=PptxElementStyle)
    manualOverrides: PptxManualOverrides = Field(default_factory=PptxManualOverrides)


class PptxSlide(BaseModel):
    id: str
    deckId: str
    index: int = Field(ge=1)
    sectionId: str | None = None
    title: str = ""
    layoutType: str = "unknown"
    background: dict[str, str] = Field(
        default_factory=lambda: {"type": "color", "value": "#FFFFFF"}
    )
    elements: list[PptxElement] = Field(default_factory=list)
    notes: str = ""
    source: dict[str, str] = Field(default_factory=dict)
    contentHash: str = ""
    layoutHash: str = ""
    visualHash: str = ""
    summaryHash: str = ""


class PptxDeck(BaseModel):
    id: str
    title: str
    sourceType: str = "pptx"
    revision: int = 0
    canvas: PptxCanvas
    theme: PptxTheme = Field(default_factory=PptxTheme)
    slides: list[PptxSlide] = Field(default_factory=list)


class PptxDeckReadiness(BaseModel):
    status: Literal["ready", "partial", "failed"] = "ready"
    message: str = "Ready"


class PptxDeckResponse(BaseModel):
    path: str
    filename: str
    source_url: str | None = None
    readiness: PptxDeckReadiness = Field(default_factory=PptxDeckReadiness)
    deck: PptxDeck


class PptxOperation(BaseModel):
    type: PptxOperationType
    slideId: str | None = None
    elementId: str | None = None
    content: str | None = None
    style: PptxElementStyle | None = None
    element: PptxElement | None = None
    x: int | None = Field(default=None, ge=0)
    y: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    layoutId: str | None = None
    respectManualOverrides: bool = True
    afterSlideId: str | None = None
    slideIdOrder: list[str] | None = None
    templateId: str | None = None
    contentMap: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_operation_shape(self) -> "PptxOperation":
        if self.type in {
            "updateText",
            "updateStyle",
            "deleteElement",
            "moveElement",
            "resizeElement",
        } and (not self.slideId or not self.elementId):
            raise ValueError(f"{self.type} requires slideId and elementId.")
        if self.type == "updateText" and self.content is None:
            raise ValueError("updateText requires content.")
        if self.type == "updateStyle" and self.style is None:
            raise ValueError("updateStyle requires style.")
        if self.type == "addElement" and (not self.slideId or self.element is None):
            raise ValueError("addElement requires slideId and element.")
        if self.type == "moveElement" and (self.x is None or self.y is None):
            raise ValueError("moveElement requires x and y.")
        if self.type == "resizeElement" and (
            self.width is None or self.height is None
        ):
            raise ValueError("resizeElement requires width and height.")
        if self.type == "applyLayout" and (not self.slideId or not self.layoutId):
            raise ValueError("applyLayout requires slideId and layoutId.")
        if self.type == "reorderSlides" and not self.slideIdOrder:
            raise ValueError("reorderSlides requires slideIdOrder.")
        if self.type == "deleteSlide" and not self.slideId:
            raise ValueError("deleteSlide requires slideId.")
        return self


class PptxOperationRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    path: str = Field(min_length=1)
    origin: PptxOperationOrigin = "user"
    expected_revision: int = Field(ge=0)
    operations: list[PptxOperation] = Field(min_length=1)


class PptxOperationResponse(BaseModel):
    path: str
    revision: int
    changed_slide_ids: list[str]
    rejected_operations: list[dict[str, Any]] = Field(default_factory=list)
    deck: PptxDeck


class PptxSearchResponse(BaseModel):
    matches: list[dict[str, Any]]


class PptxExportRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    path: str = Field(min_length=1)


class PptxExportResponse(BaseModel):
    file_id: str
    filename: str
    download_url: str
    job_id: str
