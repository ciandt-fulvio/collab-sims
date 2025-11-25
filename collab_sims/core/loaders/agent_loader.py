"""Agent loader for reading agent markdown files."""

import re
from pathlib import Path

from collab_sims.core.loaders.md_parser import (
    MarkdownDocument,
    parse_markdown_with_frontmatter,
)


class AgentLoader:
    """Loader for agent markdown files."""

    def __init__(self, base_path: str | Path = "data/definition/agents"):
        """Initialize the agent loader.

        Args:
            base_path: Base directory containing agent MD files
        """
        self.base_path = Path(base_path)

    def list_agents(self) -> list[dict]:
        """List all available agents.

        Returns:
            List of agent metadata dictionaries
        """
        if not self.base_path.exists():
            return []

        agents = []
        for md_file in self.base_path.glob("*.md"):
            try:
                doc = parse_markdown_with_frontmatter(md_file)
                agent_data = {
                    "name": doc.frontmatter.get("name", md_file.stem),
                    "description": doc.frontmatter.get("description"),
                    "tools": doc.frontmatter.get("tools"),
                    **doc.frontmatter,
                }
                agents.append(agent_data)
            except Exception as e:
                print(f"Error loading agent {md_file}: {e}")
                continue

        return sorted(agents, key=lambda a: a.get("name", ""))

    def get_agent(self, name: str) -> MarkdownDocument | None:
        """Get a specific agent by name.

        Args:
            name: Agent name (without .md extension)

        Returns:
            MarkdownDocument if found, None otherwise
        """
        file_path = self.base_path / f"{name}.md"

        if not file_path.exists():
            return None

        try:
            return parse_markdown_with_frontmatter(file_path)
        except Exception as e:
            print(f"Error loading agent {name}: {e}")
            return None

    def save_agent(self, name: str, content: str) -> bool:
        """Save or update an agent markdown file.

        Args:
            name: Agent name (without .md extension)
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
            print(f"Error saving agent {name}: {e}")
            return False

    def get_versions(self, base_name: str) -> list[str]:
        """Find all versioned files for a base name.

        Args:
            base_name: Base filename without extension (e.g., 'facilitator')

        Returns:
            List of version filenames (e.g., ['facilitator_v01.md', 'facilitator_v02.md'])
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
            Next version filename (e.g., 'facilitator_v03.md')
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
        """Save new version of agent document.

        Args:
            base_name: Base filename without extension
            content: Full markdown content (including frontmatter)

        Returns:
            New filename (e.g., 'facilitator_v03.md')
        """
        new_filename = self.get_next_version_name(base_name)
        file_path = self.base_path / new_filename

        self.base_path.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

        return new_filename
