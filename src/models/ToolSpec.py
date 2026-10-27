"""Model describing a tool exposed by the MCP server."""
from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """Description of one tool exposed by the MCP server."""

    name: str = Field(
        ...,
        description="name of tool"
    )
    description: str = Field(
        default="",
        description="Description of tool"
    )
    input_schema: dict = Field(
        default_factory=dict,
        description="Argument of tool"
    )
