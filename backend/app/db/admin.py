"""Privileged operator CLI. No role assignment is exposed in user requests."""

import argparse
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import User, AuditLog


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--revoke", action="store_true")
    args = parser.parse_args()
    with SessionLocal.begin() as db:
        user = db.scalar(select(User).where(User.username == args.username.lower()))
        if not user:
            raise SystemExit("Account not found. Register it first.")
        user.role = "user" if args.revoke else "admin"
        db.add(AuditLog(actor_id=None, action="operator_role_change", target_id=user.id, detail={"role": user.role}))
    print("Role updated.")


if __name__ == "__main__":
    main()
