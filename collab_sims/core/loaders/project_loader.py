"""Project loader for reading project markdown files."""

import re
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

    def get_versions(self, base_name: str) -> list[str]:
        """Find all versioned files for a base name.

        Args:
            base_name: Base filename without extension (e.g., 'design-sprint-q1')

        Returns:
            List of version filenames (e.g., ['design-sprint-q1_v01.md', 'design-sprint-q1_v02.md'])
        """
        if not self.base_path.exists():
            return []

        pattern = f"{base_name}_v*.md"
        version_files = sorted(self.base_path.glob(pattern))
        return [f.name for f in version_files]

    def get_next_version_name(self, base_name: str) -> str:
        """Generate next version filename.

        Args:
            base_name: Base filename without extension

        Returns:
            Next version filename (e.g., 'design-sprint-q1_v03.md')
        """
        versions = self.get_versions(base_name)

        if not versions:
            return f"{base_name}_v01.md"

        # Extract version numbers
        version_nums = []
        for v in versions:
            match = re.search(r"_v(\d+)\.md$", v)
            if match:
                version_nums.append(int(match.group(1)))

        next_num = max(version_nums) + 1 if version_nums else 1
        return f"{base_name}_v{next_num:02d}.md"

    def save_version(self, base_name: str, content: str) -> str:
        """Save new version of project document.

        Args:
            base_name: Base filename without extension
            content: Full markdown content (including frontmatter)

        Returns:
            New filename (e.g., 'design-sprint-q1_v03.md')
        """
        new_filename = self.get_next_version_name(base_name)
        file_path = self.base_path / new_filename

        self.base_path.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return new_filename
