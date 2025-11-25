"""Library API routes for accessing projects, types, scripts, and agents."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from collab_sims.core.loaders.activity_script_loader import ActivityScriptLoader
from collab_sims.core.loaders.agent_loader import AgentLoader
from collab_sims.core.loaders.process_type_loader import ProcessTypeLoader
from collab_sims.core.loaders.project_loader import ProjectLoader

router = APIRouter(prefix="/api/library", tags=["library"])

# Initialize loaders
project_loader = ProjectLoader()
process_type_loader = ProcessTypeLoader()
activity_script_loader = ActivityScriptLoader()
agent_loader = AgentLoader()


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""

    name: str
    content: str


class ProjectUpdateRequest(BaseModel):
    """Request model for updating a project."""

    content: str


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
    """Create a new project markdown file.

    Args:
        request: Project creation request with name and content

    Returns:
        Success message and project name

    Raises:
        HTTPException: If project creation fails
    """
    success = project_loader.save_project(request.name, request.content)

    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to create project '{request.name}'"
        )

    return {"message": "Project created successfully", "name": request.name}


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
        raise HTTPException(
            status_code=500, detail=f"Failed to update project '{name}'"
        )

    return {"message": "Project updated successfully", "name": name}


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
        raise HTTPException(
            status_code=404, detail=f"Process type '{process_type_id}' not found"
        )

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
        raise HTTPException(
            status_code=404, detail=f"Activity script '{name}' not found"
        )

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
        raise HTTPException(
            status_code=404, detail=f"Activity script '{name}' not found"
        )

    success = activity_script_loader.save_activity_script(name, request.content)

    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to update activity script '{name}'"
        )

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
        raise HTTPException(
            status_code=500, detail=f"Failed to update agent '{name}'"
        )

    return {"message": "Agent updated successfully", "name": name}
