"""Small, deterministic meal-plan optimizer used by the demo server.

The food numbers are deliberately small demo data, not a clinical nutrition DB.
"""
from __future__ import annotations

from itertools import product

NUTRIENTS = ("kcal", "protein", "fiber", "calcium", "iron")

FOODS = {
    "현미밥": {"kcal": 310, "protein": 6, "fiber": 3.8, "calcium": 20, "iron": 1.1, "cost": 700, "tags": []},
    "잡곡밥": {"kcal": 295, "protein": 5.5, "fiber": 3.2, "calcium": 18, "iron": 1.0, "cost": 750, "tags": []},
    "통밀빵": {"kcal": 260, "protein": 9, "fiber": 5.0, "calcium": 80, "iron": 2.2, "cost": 900, "tags": ["gluten"]},
    "닭가슴살구이": {"kcal": 185, "protein": 35, "fiber": 0, "calcium": 12, "iron": 0.9, "cost": 2400, "tags": []},
    "두부조림": {"kcal": 210, "protein": 18, "fiber": 2.0, "calcium": 380, "iron": 4.2, "cost": 1600, "tags": ["soy"]},
    "연어구이": {"kcal": 230, "protein": 25, "fiber": 0, "calcium": 18, "iron": 0.7, "cost": 3600, "tags": ["fish"]},
    "계란찜": {"kcal": 160, "protein": 13, "fiber": 0, "calcium": 65, "iron": 1.8, "cost": 1200, "tags": ["egg"]},
    "시금치나물": {"kcal": 55, "protein": 3.5, "fiber": 3.2, "calcium": 145, "iron": 2.7, "cost": 700, "tags": []},
    "브로콜리": {"kcal": 65, "protein": 4.3, "fiber": 4.5, "calcium": 70, "iron": 1.1, "cost": 850, "tags": []},
    "콩나물무침": {"kcal": 70, "protein": 5.5, "fiber": 2.6, "calcium": 45, "iron": 1.4, "cost": 600, "tags": ["soy"]},
    "바나나": {"kcal": 105, "protein": 1.3, "fiber": 3.1, "calcium": 6, "iron": 0.3, "cost": 700, "tags": []},
    "사과": {"kcal": 95, "protein": 0.5, "fiber": 4.4, "calcium": 10, "iron": 0.2, "cost": 800, "tags": []},
    "군고구마": {"kcal": 180, "protein": 3.0, "fiber": 4.8, "calcium": 35, "iron": 0.9, "cost": 900, "tags": []},
    "우유": {"kcal": 130, "protein": 7, "fiber": 0, "calcium": 260, "iron": 0.1, "cost": 700, "tags": ["dairy"]},
    "플레인요거트": {"kcal": 140, "protein": 8, "fiber": 0, "calcium": 220, "iron": 0.1, "cost": 1000, "tags": ["dairy"]},
}

# Each candidate is a meal-sized, deliberately human-readable combination.
MEALS = {
    "아침": [
        ["통밀빵", "계란찜", "바나나", "우유"],
        ["현미밥", "두부조림", "시금치나물", "우유"],
        ["잡곡밥", "계란찜", "브로콜리", "사과"],
    ],
    "점심": [
        ["현미밥", "닭가슴살구이", "브로콜리"],
        ["잡곡밥", "두부조림", "시금치나물"],
        ["현미밥", "연어구이", "콩나물무침"],
    ],
    "저녁": [
        ["잡곡밥", "닭가슴살구이", "시금치나물"],
        ["현미밥", "두부조림", "브로콜리"],
        ["잡곡밥", "연어구이", "브로콜리"],
    ],
    "간식": [["플레인요거트", "사과"], ["우유", "바나나"], ["플레인요거트", "바나나"], ["군고구마", "사과"]],
}


def targets(age: int, sex: str, activity: str) -> dict[str, float]:
    """A transparent demo target model; not KDRI or medical guidance."""
    base_kcal = 2100 if sex == "female" else 2400
    activity_delta = {"low": -150, "medium": 0, "high": 250}.get(activity, 0)
    # Growth-stage difference is intentionally modest and visible to users.
    age_delta = 100 if age >= 16 else 0
    return {
        "kcal": base_kcal + activity_delta + age_delta,
        "protein": 55 if sex == "female" else 65,
        "fiber": 25,
        "calcium": 1000,
        "iron": 15 if sex == "female" else 11,
    }


def _totals(meals: dict[str, list[str]]) -> dict[str, float]:
    result = {key: 0.0 for key in (*NUTRIENTS, "cost")}
    for items in meals.values():
        for name in items:
            for key in result:
                result[key] += FOODS[name][key]
    return result


def _is_allowed(items: list[str], exclusions: set[str]) -> bool:
    for name in items:
        if name in exclusions or exclusions.intersection(FOODS[name]["tags"]):
            return False
    return True


def _score(total: dict[str, float], target: dict[str, float], budget: int) -> float:
    weights = {"kcal": 1.0, "protein": 1.35, "fiber": 1.2, "calcium": 1.15, "iron": 1.2}
    nutrient_gap = sum(weights[key] * abs(total[key] - target[key]) / target[key] for key in NUTRIENTS)
    # Going under protein/fiber/calcium/iron is more costly than going over.
    shortfall = sum(
        weights[key] * max(0, target[key] - total[key]) / target[key]
        for key in ("protein", "fiber", "calcium", "iron")
    )
    over_budget = max(0, total["cost"] - budget) / max(budget, 1)
    return round(nutrient_gap + shortfall * 0.7 + over_budget * 7, 6)


def optimize(payload: dict) -> dict:
    try:
        age = int(payload.get("age", 16))
        budget = int(payload.get("budget", 12000))
    except (TypeError, ValueError) as exc:
        raise ValueError("나이와 예산은 숫자로 입력해 주세요.") from exc
    if not 13 <= age <= 18:
        raise ValueError("이 데모는 13~18세 청소년 입력만 지원합니다.")
    if budget < 3000:
        raise ValueError("예산은 3,000원 이상으로 입력해 주세요.")
    sex = payload.get("sex", "female")
    activity = payload.get("activity", "medium")
    if sex not in {"female", "male"} or activity not in {"low", "medium", "high"}:
        raise ValueError("성별 또는 활동량 값이 올바르지 않습니다.")
    exclusions = {str(value).strip().lower() for value in payload.get("exclusions", []) if str(value).strip()}
    target = targets(age, sex, activity)
    candidates = []
    for breakfast, lunch, dinner, snack in product(MEALS["아침"], MEALS["점심"], MEALS["저녁"], MEALS["간식"]):
        plan = {"아침": breakfast, "점심": lunch, "저녁": dinner, "간식": snack}
        if not all(_is_allowed(items, exclusions) for items in plan.values()):
            continue
        total = _totals(plan)
        candidates.append((_score(total, target, budget), total, plan))
    if not candidates:
        raise ValueError("현재 제외 조건으로 만들 수 있는 식단이 없습니다. 제외 항목을 줄여 주세요.")
    _, total, plan = min(candidates, key=lambda item: item[0])
    ratios = {key: round(total[key] / target[key] * 100) for key in NUTRIENTS}
    constraints = {
        "예산": total["cost"] <= budget,
        "알레르기·제외 식품": True,
        "열량 범위(목표의 80~120%)": 80 <= ratios["kcal"] <= 120,
        "단백질(목표의 80% 이상)": ratios["protein"] >= 80,
        "식이섬유(목표의 70% 이상)": ratios["fiber"] >= 70,
    }
    gaps = {key: round(total[key] - target[key], 1) for key in NUTRIENTS}
    return {
        "meals": plan,
        "totals": {key: round(value, 1) for key, value in total.items()},
        "targets": target,
        "ratios": ratios,
        "gaps": gaps,
        "constraints": constraints,
        "all_constraints_met": all(constraints.values()),
        "method": "소규모 후보 식단을 전수 비교해 영양 목표 차이와 예산 초과 패널티가 가장 작은 조합을 선택했습니다.",
    }
