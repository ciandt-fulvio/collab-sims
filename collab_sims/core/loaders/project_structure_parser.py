"""
Project Structure Parser

Parses and serializes project markdown files with embedded process structure.
Projects are self-contained and do not depend on external process_type YAMLs at runtime.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ActivityResult:
    """Activity result file reference."""

    filename: str
    date: str


@dataclass
class DefinitionOfDoneItem:
    """Definition of Done checkbox item."""

    text: str
    checked: bool


@dataclass
class Activity:
    """Activity within a stage."""

    id: str
    title: str
    required: bool
    path: str
    description: str
    definition_of_done: list[DefinitionOfDoneItem] = field(default_factory=list)
    activity_results: list[ActivityResult] = field(
        default_factory=list
    )  # Merged at runtime


@dataclass
class Stage:
    """Stage within a project process."""

    id: str
    title: str
    description: str
    activities: list[Activity] = field(default_factory=list)


@dataclass
class ProjectStructure:
    """Complete project structure with stages and activities."""

    stages: list[Stage] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "stages": [
                {
                    "id": stage.id,
                    "title": stage.title,
                    "description": stage.description,
                    "activities": [
                        {
                            "id": activity.id,
                            "title": activity.title,
                            "required": activity.required,
                            "path": activity.path,
                            "description": activity.description,
                            "definition_of_done": [
                                {"text": item.text, "checked": item.checked}
                                for item in activity.definition_of_done
                            ],
                            "activity_results": [
                                {"filename": result.filename, "date": result.date}
                                for result in activity.activity_results
                            ],
                            "completed": len(activity.activity_results) > 0,
                        }
                        for activity in stage.activities
                    ],
                    "completion_count": sum(
                        1
                        for activity in stage.activities
                        if activity.activity_results
                    ),
                    "total_activities": len(stage.activities),
                }
                for stage in self.stages
            ]
        }


def parse_project_structure(markdown_content: str) -> ProjectStructure:
    """
    Parse project structure from markdown body.

    Expected format:
    ## Process Structure

    ### Stage N: Title
    **Description:** Stage description

    #### Activity: Activity Title
    **ID:** activity-id
    **Required:** Yes/No
    **Path:** path/to/script.md
    **Description:** Activity description

    **Definition of Done:**
    - [ ] Unchecked item
    - [x] Checked item

    **Activity Results:**
    - filename.md (2025-01-01)

    ---

    Args:
        markdown_content: Full markdown content of project file

    Returns:
        ProjectStructure object
    """
    structure = ProjectStructure()

    # Find the Process Structure section
    process_section_match = re.search(
        r"^## Process Structure\s*$", markdown_content, re.MULTILINE
    )
    if not process_section_match:
        return structure  # No structure defined yet

    # Extract content after Process Structure header
    content_after_header = markdown_content[process_section_match.end() :]

    # Find all stages (### Stage N: Title)
    stage_pattern = r"^### Stage \d+: (.+?)$"
    stage_matches = list(re.finditer(stage_pattern, content_after_header, re.MULTILINE))

    for i, stage_match in enumerate(stage_matches):
        stage_title = stage_match.group(1).strip()

        # Extract content for this stage (until next stage or end)
        stage_start = stage_match.end()
        if i + 1 < len(stage_matches):
            stage_end = stage_matches[i + 1].start()
        else:
            stage_end = len(content_after_header)

        stage_content = content_after_header[stage_start:stage_end]

        # Extract stage description
        desc_match = re.search(
            r"^\*\*Description:\*\*\s*(.+?)$", stage_content, re.MULTILINE
        )
        stage_description = desc_match.group(1).strip() if desc_match else ""

        # Generate stage ID from title
        stage_id = "stage-" + re.sub(r"[^a-z0-9]+", "-", stage_title.lower()).strip("-")

        stage = Stage(id=stage_id, title=stage_title, description=stage_description)

        # Find all activities within this stage (#### Activity: Title)
        activity_pattern = r"^#### Activity: (.+?)$"
        activity_matches = list(
            re.finditer(activity_pattern, stage_content, re.MULTILINE)
        )

        for j, activity_match in enumerate(activity_matches):
            activity_title = activity_match.group(1).strip()

            # Extract content for this activity (until next activity or end)
            activity_start = activity_match.end()
            if j + 1 < len(activity_matches):
                activity_end = activity_matches[j + 1].start()
            else:
                activity_end = len(stage_content)

            activity_content = stage_content[activity_start:activity_end]

            # Parse activity metadata
            id_match = re.search(
                r"^\*\*ID:\*\*\s*(.+?)$", activity_content, re.MULTILINE
            )
            required_match = re.search(
                r"^\*\*Required:\*\*\s*(.+?)$", activity_content, re.MULTILINE
            )
            path_match = re.search(
                r"^\*\*Path:\*\*\s*(.+?)$", activity_content, re.MULTILINE
            )
            desc_match = re.search(
                r"^\*\*Description:\*\*\s*(.+?)$", activity_content, re.MULTILINE
            )

            activity_id = id_match.group(1).strip() if id_match else ""
            required_text = required_match.group(1).strip() if required_match else "No"
            activity_path = path_match.group(1).strip() if path_match else ""
            activity_description = desc_match.group(1).strip() if desc_match else ""

            activity = Activity(
                id=activity_id,
                title=activity_title,
                required=required_text.lower() in ["yes", "true"],
                path=activity_path,
                description=activity_description,
            )

            # Parse Definition of Done checkboxes
            dod_section_match = re.search(
                r"^\*\*Definition of Done:\*\*\s*$(.+?)(?=^\*\*|^---|$)",
                activity_content,
                re.MULTILINE | re.DOTALL,
            )
            if dod_section_match:
                dod_content = dod_section_match.group(1)
                checkbox_pattern = r"^- \[([ x])\] (.+?)$"
                for checkbox_match in re.finditer(
                    checkbox_pattern, dod_content, re.MULTILINE
                ):
                    checked = checkbox_match.group(1) == "x"
                    text = checkbox_match.group(2).strip()
                    activity.definition_of_done.append(
                        DefinitionOfDoneItem(text=text, checked=checked)
                    )

            # Parse Activity Results (these are dynamically merged, but we read them if present)
            results_section_match = re.search(
                r"^\*\*Activity Results:\*\*\s*$(.+?)(?=^---|$)",
                activity_content,
                re.MULTILINE | re.DOTALL,
            )
            if results_section_match:
                results_content = results_section_match.group(1)
                result_pattern = r"^- (.+?\.md) \((\d{4}-\d{2}-\d{2})\)"
                for result_match in re.finditer(
                    result_pattern, results_content, re.MULTILINE
                ):
                    filename = result_match.group(1).strip()
                    date = result_match.group(2).strip()
                    activity.activity_results.append(
                        ActivityResult(filename=filename, date=date)
                    )

            stage.activities.append(activity)

        structure.stages.append(stage)

    return structure


def serialize_project_structure(structure: ProjectStructure) -> str:
    """
    Serialize project structure to markdown format.

    Args:
        structure: ProjectStructure object

    Returns:
        Markdown string for Process Structure section
    """
    lines = ["## Process Structure", ""]

    for i, stage in enumerate(structure.stages, start=1):
        lines.append(f"### Stage {i}: {stage.title}")
        lines.append(f"**Description:** {stage.description}")
        lines.append("")

        for activity in stage.activities:
            lines.append(f"#### Activity: {activity.title}")
            lines.append(f"**ID:** {activity.id}")
            lines.append(f"**Required:** {'Yes' if activity.required else 'No'}")
            lines.append(f"**Path:** {activity.path}")
            lines.append(f"**Description:** {activity.description}")
            lines.append("")

            if activity.definition_of_done:
                lines.append("**Definition of Done:**")
                for item in activity.definition_of_done:
                    checkbox = "[x]" if item.checked else "[ ]"
                    lines.append(f"- {checkbox} {item.text}")
                lines.append("")

            if activity.activity_results:
                lines.append("**Activity Results:**")
                for result in activity.activity_results:
                    lines.append(f"- {result.filename} ({result.date})")
            else:
                lines.append("**Activity Results:** (none yet)")

            lines.append("")
            lines.append("---")
            lines.append("")

    return "\n".join(lines)


def update_dod_checkbox(
    markdown_content: str,
    stage_id: str,
    activity_id: str,
    item_index: int,
    checked: bool,
) -> str:
    """
    Update a specific Definition of Done checkbox in the markdown content.

    Args:
        markdown_content: Full project markdown content
        stage_id: Stage identifier
        activity_id: Activity identifier
        item_index: Index of the DoD item (0-based)
        checked: New checked state

    Returns:
        Updated markdown content

    Raises:
        ValueError: If stage, activity, or item not found
    """
    # Parse structure to validate indices
    structure = parse_project_structure(markdown_content)

    # Find the target stage and activity
    target_stage = None
    target_activity = None

    for stage in structure.stages:
        if stage.id == stage_id:
            target_stage = stage
            for activity in stage.activities:
                if activity.id == activity_id:
                    target_activity = activity
                    break
            break

    if not target_stage:
        raise ValueError(f"Stage '{stage_id}' not found")
    if not target_activity:
        raise ValueError(f"Activity '{activity_id}' not found in stage '{stage_id}'")
    if item_index < 0 or item_index >= len(target_activity.definition_of_done):
        raise ValueError(
            f"DoD item index {item_index} out of range (0-{len(target_activity.definition_of_done)-1})"
        )

    # Find the activity section in the markdown
    activity_title_escaped = re.escape(target_activity.title)
    activity_pattern = rf"^#### Activity: {activity_title_escaped}$"
    activity_match = re.search(activity_pattern, markdown_content, re.MULTILINE)

    if not activity_match:
        raise ValueError("Activity section not found in markdown")

    # Find the Definition of Done section after this activity
    activity_start = activity_match.end()

    # Find the extent of this activity section (until next #### or ###)
    next_section_match = re.search(
        r"^(####|###)", markdown_content[activity_start:], re.MULTILINE
    )
    if next_section_match:
        activity_end = activity_start + next_section_match.start()
    else:
        activity_end = len(markdown_content)

    activity_section = markdown_content[activity_start:activity_end]

    # Find DoD section
    dod_match = re.search(
        r"^\*\*Definition of Done:\*\*\s*$",
        activity_section,
        re.MULTILINE,
    )
    if not dod_match:
        raise ValueError("Definition of Done section not found")

    dod_start = activity_start + dod_match.end()

    # Find all checkbox lines
    checkbox_pattern = r"^- \[([ x])\] (.+?)$"
    checkbox_matches = list(
        re.finditer(checkbox_pattern, markdown_content[dod_start:], re.MULTILINE)
    )

    if item_index >= len(checkbox_matches):
        raise ValueError(f"DoD checkbox {item_index} not found")

    # Get the specific checkbox to update
    target_checkbox = checkbox_matches[item_index]
    checkbox_abs_start = dod_start + target_checkbox.start()
    checkbox_abs_end = dod_start + target_checkbox.end()

    # Extract the text
    current_checked = target_checkbox.group(1) == "x"
    text = target_checkbox.group(2)

    # Build new checkbox line
    new_checkbox = f"- [{'x' if checked else ' '}] {text}"

    # Replace in content
    updated_content = (
        markdown_content[:checkbox_abs_start]
        + new_checkbox
        + markdown_content[checkbox_abs_end:]
    )

    return updated_content


def update_frontmatter_timestamp(markdown_content: str) -> str:
    """
    Update the updated_at timestamp in frontmatter.

    Args:
        markdown_content: Full markdown content with frontmatter

    Returns:
        Updated markdown content with new timestamp
    """
    now = datetime.utcnow().isoformat() + "Z"

    # Match updated_at in frontmatter
    updated_pattern = r"(^---\s*$.+?^updated_at:\s*)(.+?)$"
    if re.search(updated_pattern, markdown_content, re.MULTILINE | re.DOTALL):
        # Replace existing updated_at
        updated_content = re.sub(
            updated_pattern,
            rf"\g<1>{now}",
            markdown_content,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )
    else:
        # Add updated_at if not present (after created_at or before closing ---)
        frontmatter_match = re.search(
            r"^(---\s*$.+?)(^---\s*$)", markdown_content, re.MULTILINE | re.DOTALL
        )
        if frontmatter_match:
            updated_content = (
                frontmatter_match.group(1)
                + f"updated_at: {now}\n"
                + frontmatter_match.group(2)
                + markdown_content[frontmatter_match.end() :]
            )
        else:
            # No frontmatter, return as-is
            updated_content = markdown_content

    return updated_content
