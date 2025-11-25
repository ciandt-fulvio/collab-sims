"""Project loader for reading project markdown files."""

from pathlib import Path

from collab_sims.core.loaders.md_parser import (
    MarkdownDocument,
    parse_markdown_with_frontmatter,
)


class ProjectLoader:
    """Loader for project markdown files."""

    def __init__(self, base_path: str | Path = "data/execution/projects"):
        """Initialize the project loader.

        Args:
            base_path: Base directory containing project MD files
        """
        self.base_path = Path(base_path)

    def list_projects(self) -> list[dict]:
        """List all available projects.

        Returns:
            List of project metadata dictionaries
        """
        if not self.base_path.exists():
            return []

        projects = []
        for md_file in self.base_path.glob("*.md"):
            try:
                doc = parse_markdown_with_frontmatter(md_file)
                project_data = {
                    "name": doc.frontmatter.get("name", md_file.stem),
                    "title": doc.frontmatter.get("title", md_file.stem),
                    "type": doc.frontmatter.get("type"),
                    "status": doc.frontmatter.get("status", "active"),
                    "created_at": doc.frontmatter.get("created_at"),
                    **doc.frontmatter,
                }
                projects.append(project_data)
            except Exception as e:
                print(f"Error loading project {md_file}: {e}")
                continue

        return sorted(projects, key=lambda p: p.get("created_at") or "", reverse=True)

    def get_project(self, name: str) -> MarkdownDocument | None:
        """Get a specific project by name.

        Args:
            name: Project name (without .md extension)

        Returns:
            MarkdownDocument if found, None otherwise
        """
        file_path = self.base_path / f"{name}.md"

        if not file_path.exists():
            return None

        try:
            return parse_markdown_with_frontmatter(file_path)
        except Exception as e:
            print(f"Error loading project {name}: {e}")
            return None

    def save_project(self, name: str, content: str) -> bool:
        """Save or update a project markdown file.

        Args:
            name: Project name (without .md extension)
            content: Full markdown content (including frontmatter)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            file_path = self.base_path / f"{name}.md"
            file_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error saving project {name}: {e}")
            return False
