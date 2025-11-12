from app.services.prompts.manager import PromptManager
from .highlight_detection import DDZHighlightPrompt


def register_prompts():
    PromptManager.register_prompt(DDZHighlightPrompt(), is_default=True)


__all__ = [
    "DDZHighlightPrompt",
    "register_prompts"
]
