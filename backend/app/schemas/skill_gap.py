from typing import List, Optional
from pydantic import BaseModel


class SkillGapRequest(BaseModel):
    target_role: str
    current_skills: List[str]


class PriorityItem(BaseModel):
    skill: str
    priority: str          # High / Medium / Low
    priority_score: float
    reasons: List[str]


class SkillGapResponse(BaseModel):
    target_role: str
    matched_skills: List[str]
    missing_skills: List[str]
    match_percentage: float
    weighted_match_score: float
    learning_priorities: List[PriorityItem]
