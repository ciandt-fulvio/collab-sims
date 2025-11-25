"""Process type loader for reading process type YAML files."""

from pathlib import Path

import yaml


class ProcessTypeLoader:
    """Loader for process type YAML files."""

    def __init__(self, base_path: str | Path = "data/definition/process_types"):
        """Initialize the process type loader.

        Args:
            base_path: Base directory containing process type YAML files
        """
        self.base_path = Path(base_path)

    def list_process_types(self) -> list[dict]:
        """List all available process types.

        Returns:
            List of process type metadata dictionaries
        """
        if not self.base_path.exists():
            return []

        types = []
        for yaml_file in self.base_path.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    type_data = {
                        "id": data.get("id", yaml_file.stem),
                        "title": data.get("title", yaml_file.stem),
                        "summary": data.get("summary"),
                        "agents": data.get("agents", []),
                        "stages": data.get("stages", []),
                        **data,
                    }
                    types.append(type_data)
            except Exception as e:
                print(f"Error loading process type {yaml_file}: {e}")
                continue

        return sorted(types, key=lambda t: t.get("id", ""))

    def get_process_type(self, process_type_id: str) -> dict | None:
        """Get a specific process type by ID.

        Args:
            process_type_id: Process type ID (without .yaml extension)

        Returns:
            Dict with process type data if found, None otherwise
        """
        file_path = self.base_path / f"{process_type_id}.yaml"

        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading process type {process_type_id}: {e}")
            return None

    def save_process_type(self, process_type_id: str, data: dict) -> bool:
        """Save or update a process type YAML file.

        Args:
            process_type_id: Process type ID (without .yaml extension)
            data: Process type data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            file_path = self.base_path / f"{process_type_id}.yaml"
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"Error saving process type {process_type_id}: {e}")
            return False
