import json

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.services import skill_gap_service
from backend.app.services.auth_service import get_current_user


router = APIRouter(
    prefix="/api/skill-gap",
    tags=["skill-gap"],
)


@router.post("/analyze")
async def analyze(
    target_role: str = Form(...),
    current_skills: str = Form("[]"),
    resume: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze a candidate's skill gap.

    Input:
        target_role       -> selected target role
        current_skills    -> JSON array of manually entered skills
        resume            -> optional PDF/DOCX resume

    Resume skills and manually entered skills are combined.
    """

    # -------------------------------------------------------
    # Validate target role
    # -------------------------------------------------------

    target_role = target_role.strip()

    if not target_role:
        raise HTTPException(
            status_code=400,
            detail="Target role is required.",
        )


    # -------------------------------------------------------
    # Parse manual skills
    # -------------------------------------------------------

    try:
        parsed_skills = json.loads(current_skills)

        if not isinstance(parsed_skills, list):
            parsed_skills = []

    except (json.JSONDecodeError, TypeError):
        parsed_skills = []


    manual_skills = [
        str(skill).strip()
        for skill in parsed_skills
        if str(skill).strip()
    ]


    # -------------------------------------------------------
    # Extract resume skills
    # -------------------------------------------------------

    extracted_skills = []

    if resume is not None:

        filename = (resume.filename or "").lower()

        allowed_extensions = (
            ".pdf",
            ".docx",
        )

        if not filename.endswith(
            allowed_extensions
        ):
            raise HTTPException(
                status_code=400,
                detail="Only PDF and DOCX resumes are supported.",
            )


        file_bytes = await resume.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded resume is empty.",
            )


        extracted_skills = (
            skill_gap_service.extract_resume_skills(
                db=db,
                file_bytes=file_bytes,
                filename=resume.filename or "",
            )
        )


    # -------------------------------------------------------
    # Combine skills
    # -------------------------------------------------------

    combined_skills = []

    seen = set()

    for skill in (
        extracted_skills + manual_skills
    ):

        normalized = skill.strip()

        key = normalized.lower()

        if normalized and key not in seen:

            seen.add(key)
            combined_skills.append(normalized)


    # -------------------------------------------------------
    # Validate candidate skills
    # -------------------------------------------------------

    if not combined_skills:

        return {
            "note": (
                "No skills were detected. "
                "Please upload a resume containing "
                "your skills or enter your skills manually."
            ),
            "extracted_skills": [],
            "matched_skills": [],
            "missing_skills": [],
            "learning_priorities": [],
            "match_percentage": 0,
            "weighted_match_score": 0,
        }


    # -------------------------------------------------------
    # Existing CareerPulse skill-gap engine
    # -------------------------------------------------------

    result = skill_gap_service.analyze_skill_gap(
        db,
        target_role,
        combined_skills,
    )


    # -------------------------------------------------------
    # Add extracted skills to response
    # -------------------------------------------------------

    if isinstance(result, dict):

        result["extracted_skills"] = extracted_skills

        result["candidate_skills"] = combined_skills


    return result