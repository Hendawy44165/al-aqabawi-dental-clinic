import os
import re
from dotenv import load_dotenv, find_dotenv
from langchain_openai import ChatOpenAI

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_HERE)
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)

# Load .env from backend folder, root folder, and environment
load_dotenv(find_dotenv())
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
load_dotenv(os.path.join(_ROOT_DIR, ".env"))

_PROMPTS_DIR = os.path.join(_HERE, "prompts")
THREAD_ID = "498wa1d6s5af4"


def get_model():
    """Get the shared LLM instance, supporting GitHub provider & OpenAI models."""
    api_key = os.getenv("PROVIDER_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("PROVIDER_BASE_URL")
    model_name = os.getenv("PROVIDER_MODEL_NAME", "openai/gpt-4.1")

    kwargs = {
        "model": model_name,
        "temperature": 0.3,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url

    return ChatOpenAI(**kwargs)



def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = os.path.join(_PROMPTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def parse_frontmatter(content: str) -> dict:
    """Parse YAML-like frontmatter blocks from markdown files."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            metadata = {}
            current_key = None
            for line in fm_text.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                match = re.match(r"^([a-zA-Z0-9_-]+)\s*:\s*(.*)$", line)
                if match:
                    key = match.group(1)
                    val = match.group(2).strip()
                    if val == "" or val.startswith("[") or val.startswith("-"):
                        metadata[key] = []
                        current_key = key
                    else:
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        metadata[key] = val
                        current_key = None
                elif line.startswith("-") and current_key is not None:
                    val = line[1:].strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    metadata[current_key].append(val)
            return metadata
    return {}
