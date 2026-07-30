from pydantic import BaseModel, Field
from typing import Literal


class ReviewComment(BaseModel):
    file: str = Field(description="Relative file path being commented on")
    line: int = Field(description="Line number in the file")
    severity: Literal["error", "warning", "suggestion"] = Field(
        description="How critical this comment is"
    )
    category: Literal["bug", "security", "performance", "style", "maintainability"] = Field(
        description="Category of the issue found"
    )
    message: str = Field(description="Clear explanation of the issue")
    suggested_fix: str | None = Field(
        default=None,
        description="Concrete code suggestion to fix the issue, if applicable"
    )


class ReviewOutput(BaseModel):
    comments: list[ReviewComment] = Field(
        description="All inline review comments across changed files"
    )
    overall_summary: str = Field(
        description="High level summary of the PR quality and key concerns"
    )
    score: int = Field(
        description="Code quality score from 0 (terrible) to 100 (excellent)",
        ge=0,
        le=100
    )
    approved: bool = Field(
        description="Whether this PR is safe to merge as-is"
    )