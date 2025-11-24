"""Activity script loader for reading activity script markdown files."""

from pathlib import Path

from collab_sims.core.loaders.md_parser import (
    MarkdownDocument,
    parse_markdown_with_frontmatter,
)


class ActivityScriptLoader:
    """Loader for activity script markdown files."""

    def __init__(self, base_path: str | Path = "data/activity_scripts"):
        """Initialize the activity script loader.

        Args:
            base_path: Base directory containing activity script MD files
        """
        self.base_path = Path(base_path)

    def list_activity_scripts(self) -> list[dict]:
        """List all available activity scripts.

        Returns:
            List of activity script metadata dictionaries
        """
        if not self.base_path.exists():
            return []

        scripts = []
        for md_file in self.base_path.glob("*.md"):
            try:
                doc = parse_markdown_with_frontmatter(md_file)
                script_data = {
                    "name": doc.frontmatter.get("name", md_file.stem),
                    "description": doc.frontmatter.get("description"),
                    **doc.frontmatter,
                }
                scripts.append(script_data)
            except Exception as e:
                print(f"Error loading activity script {md_file}: {e}")
                continue

        return sorted(scripts, key=lambda s: s.get("name", ""))

    def get_activity_script(self, name: str) -> MarkdownDocument | None:
        """Get a specific activity script by name.

        Args:
            name: Activity script name (without .md extension)

        Returns:
            MarkdownDocument if found, None otherwise
        """
        file_path = self.base_path / f"{name}.md"

        if not file_path.exists():
            return None

        try:
            return parse_markdown_with_frontmatter(file_path)
        except Exception as e:
            print(f"Error loading activity script {name}: {e}")
            return None

    def save_activity_script(self, name: str, content: str) -> bool:
        """Save or update an activity script markdown file.

        Args:
            name: Activity script name (without .md extension)
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
            print(f"Error saving activity script {name}: {e}")
            return False
