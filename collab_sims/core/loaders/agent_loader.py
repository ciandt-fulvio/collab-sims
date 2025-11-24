"""Agent loader for reading agent markdown files."""

from pathlib import Path

from collab_sims.core.loaders.md_parser import (
    MarkdownDocument,
    parse_markdown_with_frontmatter,
)


class AgentLoader:
    """Loader for agent markdown files."""

    def __init__(self, base_path: str | Path = "data/agents"):
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
