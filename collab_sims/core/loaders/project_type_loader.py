"""Project type loader for reading project type markdown files."""

from pathlib import Path

from collab_sims.core.loaders.md_parser import (
    MarkdownDocument,
    parse_markdown_with_frontmatter,
)


class ProjectTypeLoader:
    """Loader for project type markdown files."""

    def __init__(self, base_path: str | Path = "data/project_types"):
        """Initialize the project type loader.

        Args:
            base_path: Base directory containing project type MD files
        """
        self.base_path = Path(base_path)

    def list_project_types(self) -> list[dict]:
        """List all available project types.

        Returns:
            List of project type metadata dictionaries
        """
        if not self.base_path.exists():
            return []

        types = []
        for md_file in self.base_path.glob("*.md"):
            try:
                doc = parse_markdown_with_frontmatter(md_file)
                type_data = {
                    "name": doc.frontmatter.get("name", md_file.stem),
                    "title": doc.frontmatter.get("title", md_file.stem),
                    "description": doc.frontmatter.get("description"),
                    **doc.frontmatter,
                }
                types.append(type_data)
            except Exception as e:
                print(f"Error loading project type {md_file}: {e}")
                continue

        return sorted(types, key=lambda t: t.get("name", ""))

    def get_project_type(self, name: str) -> MarkdownDocument | None:
        """Get a specific project type by name.

        Args:
            name: Project type name (without .md extension)

        Returns:
            MarkdownDocument if found, None otherwise
        """
        file_path = self.base_path / f"{name}.md"

        if not file_path.exists():
            return None

        try:
            return parse_markdown_with_frontmatter(file_path)
        except Exception as e:
            print(f"Error loading project type {name}: {e}")
            return None
