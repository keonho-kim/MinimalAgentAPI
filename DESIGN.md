# Design System: MinimalAgent

## 1. Visual Theme & Atmosphere

MinimalAgent is a quiet local-agent workspace, not a marketing site or consumer marketplace. The interface should feel like a compact document console: calm, direct, legible, and built for repeated use while an agent streams work.

The design language is operational and flat. The main structure is a left session rail, a central chat stream, and a right file drawer. Visual weight comes from alignment, restrained borders, and text hierarchy rather than photography, gradients, large hero sections, or heavy elevation.

## 2. Color Palette & Roles

- **Warm Bone Canvas** (`#f8f7f4`): The app background. It softens the full-screen workspace without becoming decorative.
- **Paper Panel** (`#ffffff`): Primary panels, cards, the sidebar, composer, popovers, and file drawer.
- **Charcoal Ink** (`#1f2320`): Main text. It is dark enough for dense reading but avoids absolute black.
- **Quiet Secondary Ink** (`#5f625c`): Supporting labels, session metadata, file type text, placeholders, and low-priority UI text.
- **Washed Work Surface** (`#f2f1ed`): Selected sessions, reasoning events, skeletons, and neutral hover states.
- **Hairline Border** (`#e4e1da`): The default 1px divider and component outline.
- **Deep Command Black** (`#151515`): Primary actions and user chat bubbles.
- **Muted Activity Green** (`#edf3ec`): Agent activity state backgrounds.
- **Activity Green Ink** (`#315f36`): Text and icons on activity surfaces.
- **Restrained Error Red** (`#9f2f2d`): Error text, destructive actions, and failure state borders.

## 3. Typography Rules

Use a native-feeling sans stack for all UI: `SF Pro Display`, `Geist Sans`, `Helvetica Neue`, `Arial`, `sans-serif`. Use `SF Mono`, `Geist Mono`, `JetBrains Mono`, `monospace` for code, stream metadata, and compact identifiers.

The hierarchy should stay compact. Product and section titles use 14-16px with medium or semibold weight. Labels and metadata use 11-12px with muted color. Chat content uses 14px with a generous line height so markdown, code, and streamed prose remain readable.

Do not use oversized editorial display type. MinimalAgent is a tool surface; headings should help orientation, not dominate the workflow.

## 4. Component Stylings

- **Shell:** Full-height workspace with a fixed left rail on desktop and header-level session controls on small screens.
- **Panels:** White paper surfaces with a 1px hairline border. Corners are subtly rounded at 8px or less. No nested decorative cards.
- **Buttons:** Primary buttons use Deep Command Black with white text. Secondary and ghost buttons use neutral surfaces and border/hover changes only. Icon buttons stay square with 8px corners.
- **Inputs:** White or paper-toned fields with 1px hairline borders, compact height, and visible black focus rings. No glow effects.
- **Chat Messages:** Assistant messages use white panels. User messages use Deep Command Black. Reasoning uses Washed Work Surface. Activity uses Muted Activity Green. Errors use a pale red surface with restrained red borders.
- **Badges:** Badges are small, rectangular, and quiet. Use them for operational state, not decoration.
- **File Drawer:** The file drawer is a working panel with upload controls, refresh, empty state, and compact file rows. Internal workspace paths must never be exposed.

## 5. Layout Principles

Keep the app dense but readable. Desktop uses a 288px session rail, a centered chat column, and a right-side drawer. The chat column should cap near 900px so long assistant responses remain readable. Composer controls stay pinned at the bottom of the chat region.

Mobile keeps the chat as the primary surface and exposes the minimum necessary user/session controls in the header. Do not hide session switching or user identity behind unavailable desktop-only UI.

Whitespace is functional: 16-24px for major panel padding, 8-12px between compact controls, and 12-16px between chat messages. Avoid large empty bands, hero sections, decorative imagery, gradients, blobs, and stock visuals.

## 6. Motion & Elevation

Motion should be limited to existing loading indicators and simple interaction transitions. Use color and border transitions only. Avoid layout-shifting animation.

Elevation is nearly flat. Prefer borders over shadows. If a shadow is necessary for overlays, keep it subtle and low-opacity.
