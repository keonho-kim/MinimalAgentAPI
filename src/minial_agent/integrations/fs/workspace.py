from minial_agent.integrations.fs.errors import WorkspaceFsError
from minial_agent.integrations.upload import ensure_upload_workspace, get_workspace_root
from minial_agent.integrations.upload.models import UploadWorkspace


def get_workspace(*, user_id: str, uuid: str) -> UploadWorkspace:
    try:
        return ensure_upload_workspace(get_workspace_root(user_id, uuid))
    except ValueError as exc:
        raise WorkspaceFsError(400, str(exc)) from exc
