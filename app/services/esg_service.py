from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.db.database import SessionLocal
from app.db.models import CoinTransaction, ESGContribution, ESGGoal, Wallet

DEFAULT_GOALS = [
    ("ESG_SOCIAL_MENTORING", "Digital Literacy Mentoring", "Social", 500),
    ("ESG_GREEN_OFFICE", "Green Office Initiative", "Environment", 1000),
    ("ESG_GOVERNANCE", "Responsible AI Learning", "Governance", 700),
]


def ensure_goals() -> None:
    db = SessionLocal()
    try:
        for goal_id, title, category, target in DEFAULT_GOALS:
            if db.get(ESGGoal, goal_id) is None:
                db.add(ESGGoal(goal_id=goal_id, title=title, category=category, target_coins=target, status="pending_hr_review"))
        db.commit()
    finally:
        db.close()


def get_wallet(employee_id: str) -> dict[str, Any]:
    ensure_goals()
    db = SessionLocal()
    try:
        wallet = db.get(Wallet, employee_id)
        transactions = db.query(CoinTransaction).filter_by(employee_id=employee_id).order_by(CoinTransaction.created_at.desc()).all()
        return {
            "employee_id": employee_id,
            "balance": wallet.balance if wallet else 0,
            "transactions": [
                {"transaction_id": row.transaction_id, "event_id": row.event_id, "amount": row.amount, "reason": row.reason, "created_at": row.created_at.isoformat()}
                for row in transactions
            ],
        }
    finally:
        db.close()


def list_goals() -> list[dict[str, Any]]:
    ensure_goals()
    db = SessionLocal()
    try:
        goals = db.query(ESGGoal).all()
        return [goal_response(db, goal) for goal in goals]
    finally:
        db.close()


def goal_response(db, goal: ESGGoal) -> dict[str, Any]:
    contributions = db.query(ESGContribution).filter_by(goal_id=goal.goal_id).all()
    return {
        "goal_id": goal.goal_id,
        "title": goal.title,
        "category": goal.category,
        "description": goal.description,
        "total_contributed_coins": sum(item.coins for item in contributions),
        "contributors_count": len({item.employee_id for item in contributions}),
        "status": goal.status,
    }


def contribute(goal_id: str, employee_id: str, coins: int) -> dict[str, Any]:
    ensure_goals()
    if coins <= 0:
        raise HTTPException(status_code=422, detail="coins must be positive")
    db = SessionLocal()
    try:
        goal = db.get(ESGGoal, goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="ESG goal not found")
        wallet = db.get(Wallet, employee_id)
        if not wallet or wallet.balance < coins:
            raise HTTPException(status_code=409, detail="Insufficient Growth Coins")
        wallet.balance -= coins
        db.add(ESGContribution(goal_id=goal_id, employee_id=employee_id, coins=coins, created_at=date.today()))
        db.add(CoinTransaction(transaction_id=f"ESG_{uuid4().hex}", employee_id=employee_id, amount=-coins, reason=f"Contribution to ESG goal {goal.title}", created_at=date.today()))
        db.commit()
        return {**goal_response(db, goal), "employee_id": employee_id, "coins_spent": coins, "wallet_balance": wallet.balance}
    finally:
        db.close()


def engagement() -> dict[str, Any]:
    ensure_goals()
    db = SessionLocal()
    try:
        contributions = db.query(ESGContribution).all()
        return {
            "total_contributed_coins": sum(item.coins for item in contributions),
            "contributors_count": len({item.employee_id for item in contributions}),
            "by_category": {
                category: sum(item.coins for item in contributions if db.get(ESGGoal, item.goal_id).category == category)
                for category in {db.get(ESGGoal, item.goal_id).category for item in contributions}
            },
            "goals": [goal_response(db, goal) for goal in db.query(ESGGoal).all()],
        }
    finally:
        db.close()
