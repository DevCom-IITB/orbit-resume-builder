from dataclasses import dataclass
from typing import Literal


@dataclass
class RenderConfig:
    """Configuration options for rendering the resume."""
    compact: bool = False
    header_style: Literal["short", "long"] = "short"
    use_header: bool = True
