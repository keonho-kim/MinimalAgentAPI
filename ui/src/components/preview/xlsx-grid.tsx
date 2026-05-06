import { memo, useMemo, useState } from "react";

import type { XlsxCell, XlsxSheet } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

export const XlsxGrid = memo(function XlsxGrid({
  workbook,
}: {
  workbook: XlsxSheet[];
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const sheet = workbook[activeIndex] ?? workbook[0];
  const cellMap = useMemo(() => buildCellMap(sheet), [sheet]);

  if (!sheet) {
    return <div className="p-5 text-sm text-muted-foreground">Workbook is empty.</div>;
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <ScrollArea className="min-h-0 flex-1">
        <div className="p-4">
          <table className="border-collapse bg-card text-sm">
            <thead>
              <tr>
                <th className="sticky left-0 top-0 z-20 size-8 border bg-muted" />
                {sheet.columns.map((column) => (
                  <th
                    className="sticky top-0 z-10 border bg-muted px-2 text-center text-xs font-medium text-muted-foreground"
                    key={column.index}
                    style={{ minWidth: column.width, width: column.width }}
                  >
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sheet.rows.map((row) => (
                <tr key={row.index} style={{ height: row.height }}>
                  <th className="sticky left-0 z-10 border bg-muted px-2 text-right text-xs font-medium text-muted-foreground">
                    {row.index}
                  </th>
                  {sheet.columns.map((column) => {
                    const address = `${column.label}${row.index}`;
                    const merge = cellMap.merges.get(address);
                    if (merge?.covered) {
                      return null;
                    }
                    const cell = cellMap.cells.get(address);
                    return (
                      <td
                        className={cn(
                          "max-w-64 overflow-hidden text-ellipsis whitespace-nowrap border px-2 text-foreground",
                          cell?.style.bold ? "font-semibold" : "",
                          cell?.style.italic ? "italic" : "",
                        )}
                        colSpan={merge?.colSpan}
                        key={address}
                        rowSpan={merge?.rowSpan}
                        style={{
                          backgroundColor: cell?.style.background,
                          color: cell?.style.color,
                          textAlign: textAlign(cell),
                          minWidth: column.width,
                          width: column.width,
                        }}
                        title={cellTitle(cell)}
                      >
                        {cellDisplay(cell)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ScrollArea>
      <div className="flex min-h-11 items-end gap-1 overflow-x-auto border-t bg-card px-3 pt-2">
        {workbook.map((item, index) => (
          <button
            className={cn(
              "min-w-24 rounded-t-md border border-b-0 px-3 py-2 text-sm",
              index === activeIndex
                ? "bg-background text-foreground"
                : "bg-muted text-muted-foreground hover:text-foreground",
            )}
            key={item.id}
            onClick={() => setActiveIndex(index)}
            type="button"
          >
            <span className="block truncate">{item.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
});

function buildCellMap(sheet: XlsxSheet) {
  const cells = new Map(sheet.cells.map((cell) => [cell.address, cell]));
  const merges = new Map<
    string,
    { rowSpan?: number; colSpan?: number; covered?: boolean }
  >();

  for (const range of sheet.merged_ranges) {
    const parsed = parseRange(range);
    if (!parsed) {
      continue;
    }
    const rowSpan = parsed.endRow - parsed.startRow + 1;
    const colSpan = parsed.endColumn - parsed.startColumn + 1;
    for (let row = parsed.startRow; row <= parsed.endRow; row += 1) {
      for (let column = parsed.startColumn; column <= parsed.endColumn; column += 1) {
        const address = `${columnLabel(column)}${row}`;
        merges.set(
          address,
          row === parsed.startRow && column === parsed.startColumn
            ? { rowSpan, colSpan }
            : { covered: true },
        );
      }
    }
  }

  return { cells, merges };
}

function parseRange(range: string) {
  const match = /^([A-Z]+)(\d+):([A-Z]+)(\d+)$/.exec(range);
  if (!match) {
    return null;
  }
  return {
    startColumn: columnIndex(match[1]),
    startRow: Number(match[2]),
    endColumn: columnIndex(match[3]),
    endRow: Number(match[4]),
  };
}

function columnIndex(label: string) {
  return [...label].reduce((total, character) => {
    return total * 26 + character.charCodeAt(0) - 64;
  }, 0);
}

function columnLabel(index: number) {
  let value = index;
  let label = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    value = Math.floor((value - 1) / 26);
  }
  return label;
}

function cellDisplay(cell?: XlsxCell) {
  if (!cell) {
    return "";
  }
  if (cell.value === null) {
    return cell.formula ?? "";
  }
  return String(cell.value);
}

function cellTitle(cell?: XlsxCell) {
  if (!cell) {
    return "";
  }
  return cell.formula
    ? `${cell.address} ${cell.formula}`
    : `${cell.address} ${cellDisplay(cell)}`;
}

function textAlign(cell?: XlsxCell) {
  if (cell?.style.horizontal === "center") {
    return "center";
  }
  if (cell?.style.horizontal === "right") {
    return "right";
  }
  return typeof cell?.value === "number" ? "right" : "left";
}
