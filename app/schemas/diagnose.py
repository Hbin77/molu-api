from typing import Literal

from pydantic import BaseModel, Field

WarnKind = Literal["heat", "gas", "electric", "blade"]
Difficulty = Literal["easy", "medium", "hard", "expert_only"]
SafetyAction = Literal["proceed", "warn", "stop_call_expert"]
TrustAction = Literal["accept", "warn_badge", "research_again"]


class Device(BaseModel):
    name: str = Field(description="추정 기기 이름 (브랜드 + 모델)")
    confidence: float = Field(ge=0.0, le=1.0)


class Symptom(BaseModel):
    code: str | None = Field(default=None, description="에러 코드가 있을 경우 (예: 'E13')")
    plain: str = Field(description="비전문가 친화 한국어 설명 1~2문장")


class Step(BaseModel):
    n: int
    title: str
    desc: str
    warn: bool = False
    warn_kind: WarnKind | None = None
    requires_expert: bool = False


class Safety(BaseModel):
    triggered: bool
    reason: str | None = None
    action: SafetyAction


class Trust(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    action: TrustAction


class DiagnosisResponse(BaseModel):
    diagnosis_id: str
    device: Device
    symptom: Symptom
    technical: str = Field(description="전문 용어 그대로 (매뉴얼 톤)")
    difficulty: Difficulty
    estimated_minutes: int = Field(ge=0)
    steps: list[Step]
    safety: Safety
    sources: list[dict] = Field(default_factory=list)
    trust: Trust
    latency_ms: int


class DiagnosisError(BaseModel):
    error: str
    detail: str | None = None
