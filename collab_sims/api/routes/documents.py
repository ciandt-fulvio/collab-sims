"""Document management API routes.

Provides endpoints for loading, saving, and versioning markdown documents
(projects, activity_scripts, agents, activity_results).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from collab_sims.core.loaders import (
    ActivityResultLoader,
    ActivityScriptLoader,
    AgentLoader,
    ProjectLoader,
)

router = APIRouter()

# Initialize loaders
project_loader = ProjectLoader()
activity_script_loader = ActivityScriptLoader()
agent_loader = AgentLoader()
activity_result_loader = ActivityResultLoader()


class DocumentSaveRequest(BaseModel):
    """Request body for saving a document."""

    content: str


class DocumentResponse(BaseModel):
    """Response containing document data."""

    name: str
    type: str
    content: str
    frontmatter: dict
    versions: list[str]


@router.get("/documents/{doc_type}/{name}")
async def get_document(doc_type: str, name: str, project_name: str | None = None):
    """Load a document by type and name.

    Args:
        doc_type: Document type ('project', 'activity_script', 'agent', 'activity_result')
        name: Document name (without .md extension)
        project_name: Project name (required for activity_result type)

    Returns:
        DocumentResponse with content and metadata

    Raises:
        HTTPException: 404 if document not found, 400 for invalid parameters
    """
    if doc_type == "project":
        doc = project_loader.get_project(name)
        versions = project_loader.get_versions(name)
    elif doc_type == "activity_script":
        doc = activity_script_loader.get_activity_script(name)
        versions = activity_script_loader.get_versions(name)
    elif doc_type == "agent":
        doc = agent_loader.get_agent(name)
        versions = agent_loader.get_versions(name)
    elif doc_type == "activity_result":
        if not project_name:
            raise HTTPException(
                status_code=400,
                detail="project_name query parameter required for activity_result type",
            )
        doc = activity_result_loader.get_activity_result(project_name, name)
        # Extract base name from filename (remove date part)
        base_name = name.rsplit("_", 1)[0] if "_" in name else name.replace(".md", "")
        versions = activity_result_loader.get_versions(project_name, base_name)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {doc_type}")

    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document not found: {name}")

    return DocumentResponse(
        name=name,
        type=doc_type,
        content=doc.raw_content,
        frontmatter=doc.frontmatter,
        versions=versions,
    )


@router.put("/documents/{doc_type}/{name}")
async def save_document(
    doc_type: str, name: str, request: DocumentSaveRequest, project_name: str | None = None
):
    """Save or update a document (overwrites existing).

    Args:
        doc_type: Document type
        name: Document name (without .md extension)
        request: Document content
        project_name: Project name (required for activity_result type)

    Returns:
        Success message

    Raises:
        HTTPException: 400 for invalid parameters, 500 for save failures
    """
    success = False

    if doc_type == "project":
        success = project_loader.save_project(name, request.content)
    elif doc_type == "activity_script":
        success = activity_script_loader.save_activity_script(name, request.content)
    elif doc_type == "agent":
        success = agent_loader.save_agent(name, request.content)
    elif doc_type == "activity_result":
        if not project_name:
            raise HTTPException(
                status_code=400,
                detail="project_name query parameter required for activity_result type",
            )
        success = activity_result_loader.save_activity_result(project_name, name, request.content)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid document type: {doc_type}")

    if not success:
        raise HTTPException(status_code=500, detail="Failed to save document")

    return {"status": "success", "message": f"Document {name} saved successfully"}


@router.post("/documents/{doc_type}/{name}/version")
async def save_document_version(
    doc_type: str, name: str, request: DocumentSaveRequest, project_name: str | None = None
):
    """Save a new version of a document.

    Creates a new file with _vNN suffix (e.g., design-criteria_v01.md).

    Args:
        doc_type: Document type
        name: Base document name (without .md extension)
        request: Document content
        project_name: Project name (required for activity_result type)

    Returns:
        New filename

    Raises:
        HTTPException: 400 for invalid parameters, 500 for save failures
    """
    try:
        if doc_type == "project":
            new_filename = project_loader.save_version(name, request.content)
        elif doc_type == "activity_script":
            new_filename = activity_script_loader.save_version(name, request.content)
        elif doc_type == "agent":
            new_filename = agent_loader.save_version(name, request.content)
        elif doc_type == "activity_result":
            if not project_name:
                raise HTTPException(
                    status_code=400,
                    detail="project_name query parameter required for activity_result type",
                )
            # Extract base name from filename
            base_name = name.rsplit("_", 1)[0] if "_" in name else name.replace(".md", "")
            new_filename = activity_result_loader.save_version(
                project_name, base_name, request.content
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid document type: {doc_type}")

        return {
            "status": "success",
            "message": f"New version created: {new_filename}",
            "filename": new_filename,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create version: {str(e)}")
