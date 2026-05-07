import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { FileAction, FileTreeNode } from "@/lib/file-tree";

export function FileActionDialog({
  actionCandidate,
  actionType,
  movePath,
  operationPendingPath,
  onConfirm,
  onMovePathChange,
  onReset,
}: {
  actionCandidate: FileTreeNode | null;
  actionType: FileAction | null;
  movePath: string;
  operationPendingPath: string | null;
  onConfirm(): void;
  onMovePathChange(value: string): void;
  onReset(): void;
}) {
  return (
    <Dialog
      open={Boolean(actionCandidate)}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          onReset();
        }
      }}
    >
      <DialogContent className="w-[calc(100vw-2rem)] max-w-md gap-4 p-5">
        <DialogHeader>
          <DialogTitle>
            {actionType === "delete" ? "파일 또는 폴더 삭제" : "파일 또는 폴더 이동"}
          </DialogTitle>
          <DialogDescription className="break-words">
            {dialogDescription(actionType, actionCandidate)}
          </DialogDescription>
        </DialogHeader>
        {actionType === "move" ? (
          <Input
            aria-label="이동할 작업공간 경로"
            value={movePath}
            onChange={(event) => onMovePathChange(event.target.value)}
          />
        ) : null}
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="outline" onClick={onReset}>
            취소
          </Button>
          <Button
            disabled={Boolean(
              actionCandidate && operationPendingPath === actionCandidate.path,
            )}
            variant={actionType === "delete" ? "destructive" : "default"}
            onClick={onConfirm}
          >
            {actionType === "delete" ? "삭제" : "저장"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function dialogDescription(
  actionType: FileAction | null,
  file: FileTreeNode | null,
) {
  if (!file) {
    return "";
  }
  if (actionType === "delete") {
    return `${file.path} 및 관련 생성 산출물을 삭제합니다. 이 작업은 되돌릴 수 없습니다.`;
  }
  return `${file.path}을 이동할 작업공간 경로를 입력하세요.`;
}
