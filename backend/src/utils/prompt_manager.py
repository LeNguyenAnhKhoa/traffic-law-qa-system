from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

PROMPTS_DIR = Path(__file__).parent / "prompts"

class PromptManager:
    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(PROMPTS_DIR),
            autoescape=select_autoescape()
        )
    
    def render(self, template_name: str, **kwargs) -> str:
        template = self.env.get_template(template_name)
        return template.render(**kwargs)

prompt_manager = PromptManager()
