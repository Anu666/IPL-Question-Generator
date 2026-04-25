# API v1 routes
# All v1 endpoints are registered on this router.
# The router is mounted in main.py under the /api/v1 prefix.

from fastapi import APIRouter, HTTPException

from app.schemas.health import HealthResponse
from app.schemas.question import QuestionRequest, QuestionResponse
from app.services.health_service import get_health
from app.services.match_data_service import gather_match_context
from app.services.question_generator import generate_questions

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["Health"],
)
def health_check():
    """Returns the current health status of the API."""
    return get_health()


@router.post(
    "/questions/generate",
    response_model=QuestionResponse,
    summary="Generate pre-match MCQ questions",
    tags=["Questions"],
)
async def generate_match_questions(request: QuestionRequest):
    """
    Generate multiple-choice questions for an upcoming IPL match.

    Provide two team names and the match date. The API scrapes pre-match
    historical data then uses Gemini AI to generate MCQ questions.
    """
    try:
        context = await gather_match_context(request.team1, request.team2, request.date)
        questions = generate_questions(context, direction=request.direction)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")

    return QuestionResponse(
        team1=request.team1,
        team2=request.team2,
        date=request.date,
        questions=questions,
        total_questions=len(questions),
        total_credits=sum(q.credits for q in questions),
    )
