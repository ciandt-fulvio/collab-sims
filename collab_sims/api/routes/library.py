"""Library API routes for accessing projects, types, scripts, and agents."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from collab_sims.core.loaders.activity_result_loader import ActivityResultLoader
from collab_sims.core.loaders.activity_script_loader import ActivityScriptLoader
from collab_sims.core.loaders.agent_loader import AgentLoader
from collab_sims.core.loaders.md_parser import MarkdownDocument, parse_markdown_string
from collab_sims.core.loaders.process_type_loader import ProcessTypeLoader
from collab_sims.core.loaders.project_loader import ProjectLoader
from collab_sims.core.loaders.project_structure_parser import Activity as ActivityModel
from collab_sims.core.loaders.project_structure_parser import (
    ActivityResult,
    DefinitionOfDoneItem,
    ProjectStructure,
    Stage,
    parse_project_structure,
    serialize_project_structure,
    update_dod_checkbox,
    update_frontmatter_timestamp,
)

router = APIRouter(prefix="/api/library", tags=["library"])

# Initialize loaders
project_loader = ProjectLoader()
process_type_loader = ProcessTypeLoader()
activity_script_loader = ActivityScriptLoader()
activity_result_loader = ActivityResultLoader()
agent_loader = AgentLoader()


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""

    name: str
    content: str


class ProjectUpdateRequest(BaseModel):
    """Request model for updating a project."""

    content: str


class UpdateDoDRequest(BaseModel):
    """Request model for updating a Definition of Done checkbox."""

    stage_id: str
    activity_id: str
    item_index: int
    checked: bool
    expected_last_modified: str  # ISO timestamp for optimistic locking


# ===== Helper Functions =====


def generate_project_with_structure(doc: MarkdownDocument, process_type: dict) -> str:
    """
    Generate a complete project markdown file by embedding the process_type structure.

    Args:
        doc: Parsed markdown document (with minimal content)
        process_type: Full process type dictionary from YAML

    Returns:
        Complete markdown content with embedded structure
    """
    from datetime import datetime

    # Build frontmatter
    frontmatter_dict = doc.frontmatter.copy()
    frontmatter_dict.pop("type", None)  # Remove old 'type' field
    frontmatter_dict["process_type_id"] = process_type.get("id", "")
    frontmatter_dict["process_type_title"] = process_type.get("title", "")

    # Ensure timestamps
    if "created_at" not in frontmatter_dict:
        frontmatter_dict["created_at"] = datetime.now().strftime("%Y-%m-%d")
    if "updated_at" not in frontmatter_dict:
        frontmatter_dict["updated_at"] = datetime.now().isoformat() + "Z"

    # Build frontmatter YAML
    import yaml

    frontmatter_yaml = yaml.dump(frontmatter_dict, default_flow_style=False, allow_unicode=True)

    # Build project structure from process_type
    structure = ProjectStructure()

    for stage_data in process_type.get("stages", []):
        stage_id = stage_data.get("id", "")
        stage_title = stage_data.get("title", "")
        stage_description = stage_data.get("description", "")

        stage = Stage(id=stage_id, title=stage_title, description=stage_description)

        for activity_data in stage_data.get("activities", []):
            activity_id = activity_data.get("id", "")
            activity_title = activity_data.get("title", "")
            activity_required = activity_data.get("required", False)
            activity_path = activity_data.get("path", "")
            activity_description = activity_data.get("description", "")

            activity = ActivityModel(
                id=activity_id,
                title=activity_title,
                required=activity_required,
                path=activity_path,
                description=activity_description,
            )

            # Add definition of done items
            for dod_text in activity_data.get("definition_of_done", []):
                activity.definition_of_done.append(
                    DefinitionOfDoneItem(text=dod_text, checked=False)
                )

            stage.activities.append(activity)

        structure.stages.append(stage)

    # Serialize structure to markdown
    process_structure_markdown = serialize_project_structure(structure)

    # Combine everything
    full_content = f"---\n{frontmatter_yaml}---\n\n{doc.content}\n\n{process_structure_markdown}"

    return full_content


# ===== Projects =====


@router.get("/projects")
async def list_projects():
    """List all available projects.

    Returns:
        List of project metadata dictionaries
    """
    projects = project_loader.list_projects()
    return {"projects": projects, "count": len(projects)}


@router.get("/projects/{name}")
async def get_project(name: str):
    """Get a specific project by name.

    Args:
        name: Project name (without .md extension)

    Returns:
        Project metadata and full content

    Raises:
        HTTPException: If project not found
    """
    doc = project_loader.get_project(name)

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    return {
        "name": name,
        "frontmatter": doc.frontmatter,
        "content": doc.content,
        "raw_content": doc.raw_content,
    }


@router.post("/projects")
async def create_project(request: ProjectCreateRequest):
    """Create a new project markdown file with embedded process structure.

    The project content must include a 'type' field in frontmatter referencing
    a process_type. The endpoint will load the process_type and embed its full
    structure into the project file, making it self-contained.

    Args:
        request: Project creation request with name and content

    Returns:
        Success message and project name

    Raises:
        HTTPException: If project creation fails or process_type not found
    """
    # Parse incoming content to extract process_type reference
    doc = parse_markdown_string(request.content)

    # Extract process_type from frontmatter
    process_type_id = doc.frontmatter.get("type")

    if not process_type_id:
        raise HTTPException(
            status_code=400,
            detail="Project must specify a 'type' field in frontmatter referencing a process_type",
        )

    # Load the process_type YAML
    process_type = process_type_loader.get_process_type(process_type_id)

    if not process_type:
        raise HTTPException(
            status_code=404, detail=f"Process type '{process_type_id}' not found"
        )

    # Generate full project content with embedded structure
    full_content = generate_project_with_structure(doc, process_type)

    # Save the expanded content
    success = project_loader.save_project(request.name, full_content)

    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to create project '{request.name}'"
        )

    return {
        "message": "Project created successfully",
        "name": request.name,
        "process_type": process_type_id,
    }


@router.put("/projects/{name}")
async def update_project(name: str, request: ProjectUpdateRequest):
    """Update an existing project markdown file.

    Args:
        name: Project name (without .md extension)
        request: Project update request with new content

    Returns:
        Success message

    Raises:
        HTTPException: If project update fails
    """
    # Check if project exists
    existing = project_loader.get_project(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    success = project_loader.save_project(name, request.content)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update project '{name}'")

    return {"message": "Project updated successfully", "name": name}


@router.patch("/projects/{name}/dod")
async def update_definition_of_done(name: str, request: UpdateDoDRequest):
    """Update a Definition of Done checkbox in a project.

    Uses optimistic locking to prevent conflicts during concurrent updates.

    Args:
        name: Project name (without .md extension)
        request: DoD update request with stage/activity/item identifiers and new state

    Returns:
        Success message with updated timestamp

    Raises:
        HTTPException: If project not found, timestamp mismatch (409), or update fails
    """
    # Load project
    project_doc = project_loader.get_project(name)
    if project_doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    # Check optimistic lock - compare timestamps
    current_updated_at = project_doc.frontmatter.get("updated_at", "")
    if current_updated_at != request.expected_last_modified:
        raise HTTPException(
            status_code=409,
            detail=f"Project has been modified by another user. Expected timestamp: {request.expected_last_modified}, current: {current_updated_at}",
        )

    try:
        # Update checkbox state
        updated_content = update_dod_checkbox(
            markdown_content=project_doc.raw_content,
            stage_id=request.stage_id,
            activity_id=request.activity_id,
            item_index=request.item_index,
            checked=request.checked,
        )

        # Update timestamp
        updated_content = update_frontmatter_timestamp(updated_content)

        # Save project
        success = project_loader.save_project(name, updated_content)

        if not success:
            raise HTTPException(
                status_code=500, detail=f"Failed to save project '{name}'"
            )

        # Parse updated content to get new timestamp
        from collab_sims.core.loaders.md_parser import parse_markdown_string

        updated_doc = parse_markdown_string(updated_content)
        new_timestamp = updated_doc.frontmatter.get("updated_at", "")

        return {
            "message": "Definition of Done updated successfully",
            "name": name,
            "updated_at": new_timestamp,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{name}/process-progress")
async def get_project_process_progress(name: str):
    """Get process structure and progress for a specific project.

    Parses the embedded process structure from the project markdown body
    and enriches it with completion status based on activity result files.

    Args:
        name: Project name

    Returns:
        Project structure data enriched with completion status

    Raises:
        HTTPException: If project not found
    """
    # Load project
    project_doc = project_loader.get_project(name)
    if project_doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    # Parse structure from project body
    structure = parse_project_structure(project_doc.raw_content)

    # Load activity results to determine completion
    results = activity_result_loader.list_activity_results(name)

    # Create mapping of activity_id -> result files with dates
    activity_result_map = {}  # activity_id -> list of {filename, date}

    for result in results:
        activity_script = result.get("activity_script")
        result_date = result.get("created_at", "")
        result_filename = result.get("filename", "")

        if activity_script:
            # Match to activity IDs by script path
            for stage in structure.stages:
                for activity in stage.activities:
                    # Match by activity script path
                    if activity.path.endswith(f"{activity_script}.md"):
                        if activity.id not in activity_result_map:
                            activity_result_map[activity.id] = []
                        activity_result_map[activity.id].append(
                            {"filename": result_filename, "date": result_date}
                        )

    # Enrich structure with completion data
    for stage in structure.stages:
        for activity in stage.activities:
            # Merge activity results
            if activity.id in activity_result_map:
                activity.activity_results = [
                    ActivityResult(filename=r["filename"], date=r["date"])
                    for r in activity_result_map[activity.id]
                ]

    # Return as dictionary
    return structure.to_dict()


@router.get("/projects/{name}/activity-results")
async def get_project_activity_results(name: str):
    """Get all activity execution results for a project.

    Args:
        name: Project name

    Returns:
        Activity results grouped by activity script

    Raises:
        HTTPException: If project not found
    """
    # Verify project exists
    project_doc = project_loader.get_project(name)
    if project_doc is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    # Load and group activity results
    results = activity_result_loader.list_activity_results(name)
    grouped = activity_result_loader.group_by_activity(results)

    return {"project_name": name, "activity_groups": grouped}


# ===== Process Types =====


@router.get("/process-types")
async def list_process_types():
    """List all available process types.

    Returns:
        List of process type metadata dictionaries
    """
    types = process_type_loader.list_process_types()
    return {"process_types": types, "count": len(types)}


@router.get("/process-types/{process_type_id}")
async def get_process_type(process_type_id: str):
    """Get a specific process type by ID.

    Args:
        process_type_id: Process type ID (without .yaml extension)

    Returns:
        Process type data with stages and activities

    Raises:
        HTTPException: If process type not found
    """
    data = process_type_loader.get_process_type(process_type_id)

    if data is None:
        raise HTTPException(status_code=404, detail=f"Process type '{process_type_id}' not found")

    return data


# ===== Activity Scripts =====


@router.get("/activity-scripts")
async def list_activity_scripts():
    """List all available activity scripts.

    Returns:
        List of activity script metadata dictionaries
    """
    scripts = activity_script_loader.list_activity_scripts()
    return {"activity_scripts": scripts, "count": len(scripts)}


@router.get("/activity-scripts/{name}")
async def get_activity_script(name: str):
    """Get a specific activity script by name.

    Args:
        name: Activity script name (without .md extension)

    Returns:
        Activity script metadata and full content

    Raises:
        HTTPException: If activity script not found
    """
    doc = activity_script_loader.get_activity_script(name)

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Activity script '{name}' not found")

    return {
        "name": name,
        "frontmatter": doc.frontmatter,
        "content": doc.content,
        "raw_content": doc.raw_content,
    }


@router.put("/activity-scripts/{name}")
async def update_activity_script(name: str, request: ProjectUpdateRequest):
    """Update an existing activity script markdown file.

    Args:
        name: Activity script name (without .md extension)
        request: Activity script update request with new content

    Returns:
        Success message

    Raises:
        HTTPException: If activity script update fails
    """
    # Check if activity script exists
    existing = activity_script_loader.get_activity_script(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Activity script '{name}' not found")

    success = activity_script_loader.save_activity_script(name, request.content)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update activity script '{name}'")

    return {"message": "Activity script updated successfully", "name": name}


# ===== Agents =====


@router.get("/agents")
async def list_agents():
    """List all available agents.

    Returns:
        List of agent metadata dictionaries
    """
    agents = agent_loader.list_agents()
    return {"agents": agents, "count": len(agents)}


@router.get("/agents/{name}")
async def get_agent(name: str):
    """Get a specific agent by name.

    Args:
        name: Agent name (without .md extension)

    Returns:
        Agent metadata and full content

    Raises:
        HTTPException: If agent not found
    """
    doc = agent_loader.get_agent(name)

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    return {
        "name": name,
        "frontmatter": doc.frontmatter,
        "content": doc.content,
        "raw_content": doc.raw_content,
    }


@router.put("/agents/{name}")
async def update_agent(name: str, request: ProjectUpdateRequest):
    """Update an existing agent markdown file.

    Args:
        name: Agent name (without .md extension)
        request: Agent update request with new content

    Returns:
        Success message

    Raises:
        HTTPException: If agent update fails
    """
    # Check if agent exists
    existing = agent_loader.get_agent(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")

    success = agent_loader.save_agent(name, request.content)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update agent '{name}'")

    return {"message": "Agent updated successfully", "name": name}
