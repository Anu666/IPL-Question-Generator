# Question schemas
# Pydantic models for the MCQ question request and response.

from pydantic import BaseModel, field_validator


class MCQOption(BaseModel):
    id: int
    optionText: str


class MCQQuestion(BaseModel):
    id: int
    questionText: str
    options: list[MCQOption]
    credits: int


class QuestionRequest(BaseModel):
    team1: str   # e.g. "Mumbai Indians"
    team2: str   # e.g. "Chennai Super Kings"
    date: str    # e.g. "2026-04-28"

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        from datetime import datetime
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")
        return v


class QuestionResponse(BaseModel):
    team1: str
    team2: str
    date: str
    questions: list[MCQQuestion]
    total_questions: int
    total_credits: int
