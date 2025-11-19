"""System prompt management for Collab Sims agents."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to prompts directory (relative to collab_sims package root)
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_template(template_path: str) -> str:
    """
    Load a template file from the prompts directory.

    Args:
        template_path: Path relative to prompts/ (e.g., 'base/system.txt')

    Returns:
        Template content as string
    """
    full_path = PROMPTS_DIR / template_path

    if not full_path.exists():
        raise FileNotFoundError(
            f"Template not found: {full_path}\n"
            f"Available templates: {list(PROMPTS_DIR.rglob('*.txt')) if PROMPTS_DIR.exists() else []}"
        )

    return full_path.read_text()


def get_session_prompt(session_id: str) -> str:
    """
    Get session agent system prompt with session ID filled in.

    Composes a complete system prompt for collaborative simulation sessions.

    Args:
        session_id: Session ID (full UUID or short ID)

    Returns:
        Complete system prompt with session_id substituted
    """
    # Use short ID (first 8 chars) if full UUID provided
    short_id = session_id[:8] if len(session_id) > 8 else session_id

    logger.debug(f"🔧 Composing session prompt for {short_id}")

    try:
        # Load base templates
        system_prompt = load_template("base/system.txt").format(session_id=short_id)

        # Try to load collaboration instructions if available
        try:
            collaboration = load_template("base/collaboration.txt")
            prompt = f"{system_prompt}\n\n{collaboration}"
        except FileNotFoundError:
            # Collaboration template is optional
            prompt = system_prompt

        logger.debug(f"   ✓ Composed session prompt (total length: {len(prompt)} chars)")
        return prompt

    except FileNotFoundError as e:
        # Fallback to basic prompt if templates not yet created
        logger.warning(f"Prompt templates not found: {e}. Using fallback prompt.")
        return get_fallback_prompt(short_id)


def get_fallback_prompt(session_id: str) -> str:
    """
    Fallback system prompt when templates are not available.

    Args:
        session_id: Session ID (short)

    Returns:
        Basic system prompt
    """
    return f"""You are an AI agent in a collaborative simulation (Session: {session_id}).

Your role is to assist with tasks, answer questions, and work collaboratively with other agents.

Use the available tools to read files, execute code, and interact with the environment.
When planning complex tasks, use the TodoWrite tool to break them down into steps.

Always be helpful, accurate, and transparent about your capabilities and limitations.
"""


def list_available_prompts() -> dict[str, str]:
    """List all available prompt files with their first line."""
    prompts = {}

    if not PROMPTS_DIR.exists():
        return prompts

    for prompt_file in PROMPTS_DIR.rglob('*.txt'):
        try:
            first_line = prompt_file.read_text().split('\n')[0]
            # Make path relative to PROMPTS_DIR
            relative_path = prompt_file.relative_to(PROMPTS_DIR)
            prompts[str(relative_path)] = first_line
        except Exception as e:
            logger.warning(f"Could not read prompt {prompt_file}: {e}")

    return prompts
