"""Post-hoc safety guard: re-check Gemini's output against a hardcoded
dangerous-keyword list, in case the model under-classifies risk.
"""

from app.schemas.diagnose import DiagnosisResponse, Safety, SafetyAction

DANGER_PATTERNS: dict[str, list[str]] = {
    "gas": ["가스 밸브", "가스 누출", "가스 냄새", "LPG", "도시가스", "프로판"],
    "electric": ["감전", "노출 전선", "차단기 분해", "고전압", "220v", "변압기"],
    "blade": ["회전 칼날", "블레이드", "분쇄기 칼날", "체인쏘"],
    "heat": ["100°C", "100℃", "고온 표면", "발열 부품 직접"],
}


def reinforce_safety(diag: DiagnosisResponse) -> DiagnosisResponse:
    """If the model marked it as safe but danger keywords appear in plain/technical/steps,
    upgrade the safety verdict to stop_call_expert.
    """
    if diag.safety.action == "stop_call_expert":
        return diag

    haystack_parts: list[str] = [
        diag.symptom.plain,
        diag.technical,
    ]
    for s in diag.steps:
        haystack_parts.append(s.title)
        haystack_parts.append(s.desc)
    haystack = " ".join(haystack_parts).lower()

    for kind, patterns in DANGER_PATTERNS.items():
        for p in patterns:
            if p.lower() in haystack:
                action: SafetyAction = "stop_call_expert"
                reason = (
                    f"안전 가드(post-check): '{p}'와 관련된 작업이 감지되어 "
                    f"비전문가 진행을 만류합니다."
                )
                diag.safety = Safety(triggered=True, reason=reason, action=action)
                return diag
    return diag
