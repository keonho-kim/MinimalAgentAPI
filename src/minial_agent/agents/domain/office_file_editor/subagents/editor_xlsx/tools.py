from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.dataframe_tools import (
    load_xlsx_range,
    preview_xlsx_dataframe,
    profile_xlsx_dataframe,
    transform_xlsx_dataframe,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.export_tools import (
    commit_xlsx_session,
    export_xlsx_dataframe,
    export_xlsx_dataframe_csv,
    export_xlsx_detected_table_csv,
    export_xlsx_range,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.session_tools import (
    discard_xlsx_session,
    inspect_xlsx_session,
    start_xlsx_session,
)
from minial_agent.agents.domain.office_file_editor.subagents.editor_xlsx.write_tools import (
    add_xlsx_formula,
    write_xlsx_dataframe,
    write_xlsx_values,
)


XLSX_SESSION_TOOLS = [
    start_xlsx_session,
    inspect_xlsx_session,
    load_xlsx_range,
    profile_xlsx_dataframe,
    preview_xlsx_dataframe,
    transform_xlsx_dataframe,
    write_xlsx_dataframe,
    write_xlsx_values,
    add_xlsx_formula,
    export_xlsx_range,
    export_xlsx_dataframe,
    export_xlsx_detected_table_csv,
    export_xlsx_dataframe_csv,
    commit_xlsx_session,
    discard_xlsx_session,
]
