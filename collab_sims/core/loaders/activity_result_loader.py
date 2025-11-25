"""Activity result loader for reading activity execution result files."""

import re
from pathlib import Path

from collab_sims.core.loaders.md_parser import (
    MarkdownDocument,
    parse_markdown_with_frontmatter,
)


class ActivityResultLoader:
    """Loader for activity result markdown files."""

    def __init__(self, base_path: str | Path = "data/execution/activity_results"):
        """Initialize the activity result loader.

        Args:
            base_path: Base directory containing activity result files
        """
        self.base_path = Path(base_path)

    def list_activity_results(self, project_name: str) -> list[dict]:
        """List all activity results for a specific project.

        Args:
            project_name: Project name

        Returns:
            List of activity result metadata dictionaries
        """
        project_path = self.base_path / project_name

        if not project_path.exists():
            return []

        results = []
        for md_file in project_path.glob("*.md"):
            try:
                # Parse filename: {activity-script}_{timestamp}.md
                match = re.match(r"^(.+?)_(\d{4}-\d{2}-\d{2})\.md$", md_file.name)

                if not match:
                    print(f"Skipping file with invalid naming: {md_file.name}")
                    continue

                activity_script = match.group(1)
                date_str = match.group(2)

                # Parse markdown document
                doc = parse_markdown_with_frontmatter(md_file)

                result_data = {
                    "filename": md_file.name,
                    "activity_script": activity_script,
                    "created_at": date_str,
                    "status": doc.frontmatter.get("status", "completed"),
                    "metadata": doc.frontmatter,
                    "path": str(md_file.relative_to(self.base_path)),
                }
                results.append(result_data)
            except Exception as e:
                print(f"Error loading activity result {md_file}: {e}")
                continue

        # Sort by date (most recent first)
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return results

    def group_by_activity(self, results: list[dict]) -> list[dict]:
        """Group activity results by activity script name.

        Args:
            results: List of activity result dictionaries

        Returns:
            List of grouped results, sorted alphabetically by activity name
        """
        groups = {}

        for result in results:
            activity_script = result.get("activity_script")
            if not activity_script:
                continue

            if activity_script not in groups:
                groups[activity_script] = {
                    "activity_script": activity_script,
                    "activity_title": self._format_title(activity_script),
                    "executions": [],
                }

            groups[activity_script]["executions"].append(result)

        # Convert to list and sort alphabetically
        grouped_list = list(groups.values())
        grouped_list.sort(key=lambda g: g["activity_script"])

        return grouped_list

    def _format_title(self, activity_script: str) -> str:
        """Convert activity script name to title case.

        Args:
            activity_script: Activity script name (e.g., 'how-might-we')

        Returns:
            Formatted title (e.g., 'How Might We')
        """
        return activity_script.replace("-", " ").replace("_", " ").title()

    def get_activity_result(self, project_name: str, name: str) -> MarkdownDocument | None:
        """Get a specific activity result by name.

        Args:
            project_name: Project name
            name: Result name without .md extension (e.g., 'how-might-we_2025-01-15')

        Returns:
            MarkdownDocument if found, None otherwise
        """
        # Ensure .md extension is added (consistent with other loaders)
        filename = f"{name}.md" if not name.endswith(".md") else name
        file_path = self.base_path / project_name / filename

        if not file_path.exists():
            return None

        try:
            return parse_markdown_with_frontmatter(file_path)
        except Exception as e:
            print(f"Error loading activity result {filename}: {e}")
            return None

    def get_versions(self, project_name: str, base_name: str) -> list[str]:
        """Find all versioned files for a base name.

        Args:
            project_name: Project name
            base_name: Base filename without extension (e.g., 'design-criteria')

        Returns:
            List of version filenames (e.g., ['design-criteria_v01.md', 'design-criteria_v02.md'])
        """
        result_dir = self.base_path / project_name
        if not result_dir.exists():
            return []

        pattern = f"{base_name}_v*.md"
        version_files = sorted(result_dir.glob(pattern))
        return [f.name for f in version_files]

    def get_next_version_name(self, project_name: str, base_name: str) -> str:
        """Generate next version filename.

        Args:
            project_name: Project name
            base_name: Base filename without extension

        Returns:
            Next version filename (e.g., 'design-criteria_v03.md')
        """
        versions = self.get_versions(project_name, base_name)

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

    def save_version(self, project_name: str, base_name: str, content: str) -> str:
        """Save new version of document.

        Args:
            project_name: Project name
            base_name: Base filename without extension
            content: Full markdown content (including frontmatter)

        Returns:
            New filename (e.g., 'design-criteria_v03.md')
        """
        new_filename = self.get_next_version_name(project_name, base_name)
        file_path = self.base_path / project_name / new_filename

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return new_filename

    def save_activity_result(self, project_name: str, filename: str, content: str) -> bool:
        """Save or update an activity result document.

        Args:
            project_name: Project name
            filename: Result filename (with or without .md extension)
            content: Full markdown content (including frontmatter)

        Returns:
            True if successful, False otherwise
        """
        # Add .md extension if not present (consistency with other loaders)
        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        file_path = self.base_path / project_name / filename

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error saving activity result {filename}: {e}")
            return False
