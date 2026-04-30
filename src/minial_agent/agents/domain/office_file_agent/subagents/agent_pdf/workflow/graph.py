from minial_agent.agents.domain.office_file_agent.subagents.utils.workflow import (
    build_office_file_workflow,
)
from minial_agent.integrations.upload.models import UploadWorkspace


def build_pdf_workflow(workspace: UploadWorkspace):
    return build_office_file_workflow(workspace)
