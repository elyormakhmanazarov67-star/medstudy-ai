"""Non-transactional Premium feature catalog.

This module describes planned features only. It does NOT accept payments,
charge accounts, grant subscriptions, or enforce access. Paid functionality
requires separate legal, privacy, product and security review.
"""
from __future__ import annotations

FEATURES = {
    "free": ["lessons", "quizzes", "progress", "study_plan"],
    "premium_preview": [
        "extended_tutor_quota_planned",
        "advanced_progress_planned",
        "exam_preparation_planned",
    ],
}


def plans_catalog() -> dict:
    return {
        "status": "design_preview",
        "purchases_enabled": False,
        "subscription_processing_enabled": False,
        "plans": [
            {
                "id": "free", "name": "Bepul",
                "available": True, "price": None, "features": FEATURES["free"],
            },
            {
                "id": "premium_preview", "name": "Premium (reja)",
                "available": False, "price": None,
                "features": FEATURES["premium_preview"],
            },
        ],
        "notice": (
            "Premium hozir sotuvda emas. To‘lov tizimi ulanmagan; "
            "foydalanuvchilardan to‘lov ma’lumoti so‘ralmaydi."
        ),
    }
