import json
import shutil
from pathlib import Path
from uuid import uuid4

from minial_agent.common.utils import file_registry
from minial_agent.integrations.upload.models import UploadWorkspace
from minial_agent.integrations.upload.resolver import ResolvedUploadArtifact
from minial_agent.integrations.xlsx.dataframes import (
    load_dataframe,
    preview_dataframe,
    profile_dataframe,
    save_dataframe,
)
from minial_agent.integrations.xlsx.errors import XlsxSessionError
from minial_agent.integrations.xlsx.models import SessionChange, SessionManifest
from minial_agent.integrations.xlsx.ranges import range_to_dataframe, write_dataframe, write_formula, write_values
from minial_agent.integrations.xlsx.transforms import transform_dataframe
from minial_agent.integrations.xlsx.workbook import inspect_workbook


class XlsxSessionStore:
    def __init__(self, workspace: UploadWorkspace):
        self.workspace = workspace
        self.root = workspace.jobs_dir / "xlsx_sessions"

    def create(self, *, artifact: ResolvedUploadArtifact, instruction: str) -> "XlsxSession":
        session_id = f"xlsx_{uuid4().hex[:12]}"
        session_dir = self.root / session_id
        dataframes_dir = session_dir / "dataframes"
        dataframes_dir.mkdir(parents=True, exist_ok=False)
        working_path = session_dir / "working.xlsx"
        shutil.copyfile(artifact.source_path, working_path)
        manifest = SessionManifest(
            session_id=session_id,
            source_file_id=artifact.file_id,
            source_filename=artifact.visible_name,
            instruction=instruction,
        )
        (session_dir / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return XlsxSession(self.workspace, session_dir, manifest)

    def load(self, session_id: str) -> "XlsxSession":
        if "/" in session_id or ".." in session_id:
            raise XlsxSessionError("Invalid XLSX session id.")
        session_dir = self.root / session_id
        manifest_path = session_dir / "manifest.json"
        if not manifest_path.is_file():
            raise XlsxSessionError(f"XLSX session not found: {session_id}")
        manifest = SessionManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
        return XlsxSession(self.workspace, session_dir, manifest)


class XlsxSession:
    def __init__(self, workspace: UploadWorkspace, session_dir: Path, manifest: SessionManifest):
        self.workspace = workspace
        self.session_dir = session_dir
        self.manifest = manifest
        self.working_path = session_dir / manifest.working_filename
        self.dataframes_dir = session_dir / "dataframes"
        self.operations_path = session_dir / "operations.jsonl"

    def inspect(self) -> dict:
        return inspect_workbook(self.working_path, filename=self.manifest.source_filename).to_dict()

    def load_range(self, *, sheet: str, range_ref: str, dataframe_name: str, header: bool) -> dict:
        dataframe = range_to_dataframe(self.working_path, sheet, range_ref, header=header)
        self.save_dataframe(dataframe_name, dataframe)
        self.record("load_range", {"sheet": sheet, "range": range_ref, "dataframe": dataframe_name})
        return {
            "session_id": self.manifest.session_id,
            "dataframe": dataframe_name,
            "profile": profile_dataframe(dataframe_name, dataframe).to_dict(),
            "preview": preview_dataframe(dataframe),
        }

    def dataframe_profile(self, dataframe_name: str) -> dict:
        dataframe = self.load_dataframe(dataframe_name)
        return profile_dataframe(dataframe_name, dataframe).to_dict()

    def dataframe_preview(self, dataframe_name: str, *, max_rows: int) -> list[dict]:
        return preview_dataframe(self.load_dataframe(dataframe_name), max_rows=max_rows)

    def transform(self, *, input_dataframe: str, output_dataframe: str, code: str, explanation: str) -> dict:
        input_path = self.dataframe_path(input_dataframe)
        output_path = self.dataframe_path(output_dataframe)
        transformed = transform_dataframe(input_path=input_path, output_path=output_path, code=code)
        self.add_dataframe_name(output_dataframe)
        self.record(
            "transform_dataframe",
            {
                "input_dataframe": input_dataframe,
                "output_dataframe": output_dataframe,
                "explanation": explanation,
            },
        )
        return {
            "session_id": self.manifest.session_id,
            "dataframe": output_dataframe,
            "profile": profile_dataframe(output_dataframe, transformed).to_dict(),
            "preview": preview_dataframe(transformed),
        }

    def write_dataframe(self, *, dataframe_name: str, sheet: str, start_cell: str, include_header: bool) -> dict:
        result = write_dataframe(
            self.working_path,
            sheet,
            start_cell,
            self.load_dataframe(dataframe_name),
            include_header=include_header,
        )
        self.record("write_dataframe", {"dataframe": dataframe_name, **result})
        return result

    def write_values(self, *, sheet: str, start_cell: str, values: list[list]) -> dict:
        result = write_values(self.working_path, sheet, start_cell, values)
        self.record("write_values", result)
        return result

    def add_formula(self, *, sheet: str, cell: str, formula: str, fill_range: str | None) -> dict:
        result = write_formula(self.working_path, sheet, cell, formula, fill_range=fill_range)
        self.record("add_formula", {**result, "formula": formula})
        return result

    def save_dataframe(self, dataframe_name: str, dataframe) -> None:
        save_dataframe(self.dataframe_path(dataframe_name), dataframe)
        self.add_dataframe_name(dataframe_name)

    def load_dataframe(self, dataframe_name: str):
        path = self.dataframe_path(dataframe_name)
        if not path.is_file():
            raise XlsxSessionError(f"Dataframe not found in session: {dataframe_name}")
        return load_dataframe(path)

    def dataframe_path(self, dataframe_name: str) -> Path:
        safe_name = dataframe_name.strip()
        if not safe_name or "/" in safe_name or ".." in safe_name:
            raise XlsxSessionError("Invalid dataframe name.")
        return self.dataframes_dir / f"{safe_name}.json"

    def changed_items(self) -> list[dict]:
        if not self.operations_path.is_file():
            return []
        return [
            json.loads(line)
            for line in self.operations_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def source_artifact(self) -> ResolvedUploadArtifact:
        return file_registry.resolve_artifact(
            workspace=self.workspace,
            file_ref=self.manifest.source_file_id,
            expected_file_type="xlsx",
        )

    def discard(self) -> dict:
        shutil.rmtree(self.session_dir)
        return {"session_id": self.manifest.session_id, "discarded": True}

    def add_dataframe_name(self, dataframe_name: str) -> None:
        if dataframe_name not in self.manifest.dataframes:
            self.manifest = SessionManifest(
                session_id=self.manifest.session_id,
                source_file_id=self.manifest.source_file_id,
                source_filename=self.manifest.source_filename,
                instruction=self.manifest.instruction,
                working_filename=self.manifest.working_filename,
                dataframes=[*self.manifest.dataframes, dataframe_name],
            )
            (self.session_dir / "manifest.json").write_text(
                json.dumps(self.manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    def record(self, action: str, details: dict) -> None:
        change = SessionChange(action=action, details=details)
        with self.operations_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(change.to_dict(), ensure_ascii=False) + "\n")
