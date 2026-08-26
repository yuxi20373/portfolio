from ..integrations.llm_client import simple_completion
from ..prompts.bash_reference import BASH_PARSE_SYSTEM_PROMPT


def parse_command(command: str) -> str:
    """One-shot LLM explanation of a (possibly multi-part) shell command -
    see BashReferenceView.js's second input box."""
    return simple_completion(
        messages=[
            {"role": "system", "content": BASH_PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": command},
        ],
        temperature=0.2,
    )
