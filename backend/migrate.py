#!/usr/bin/env python3
"""Migrate data between JSON files and MongoDB storage backends."""

from __future__ import annotations

import argparse
import asyncio
import json

from backend.config import load_config as load_app_config, save_config as save_app_config
from backend.database.json_store import JsonStore, SESSIONS_DIR
from backend.database.mongo_store import MongoStore
from backend.models import OnboardingSession


async def _json_to_mongo() -> None:
    config = load_app_config()
    json_store = JsonStore()
    mongo_store = MongoStore(config)

    print("JSON → MongoDB migration")
    print("=========================")

    cfg = await json_store.get_config()
    await mongo_store.save_config(cfg)
    print("[OK] Config")

    cv = await json_store.get_cv()
    if cv:
        await mongo_store.save_cv(cv)
        print("[OK] Base CV")
    else:
        print("[SKIP] No base CV found")

    positions = await json_store.list_positions()
    for pos in positions:
        await mongo_store.save_position(pos)
    print(f"[OK] Positions ({len(positions)} migrated)")

    session_count = 0
    if SESSIONS_DIR.exists():
        for session_file in SESSIONS_DIR.glob("*.json"):
            with open(session_file) as f:
                session = OnboardingSession(**json.load(f))
            await mongo_store.save_onboarding_session(session)
            session_count += 1
    print(f"[OK] Onboarding sessions ({session_count} migrated)")

    cfg.storage_backend = "mongodb"
    save_app_config(cfg)
    print("\nMigration complete. Storage backend set to 'mongodb'.")


async def _mongo_to_json() -> None:
    config = load_app_config()
    mongo_store = MongoStore(config)
    json_store = JsonStore()

    print("MongoDB → JSON migration")
    print("=========================")

    cfg = await mongo_store.get_config()
    await json_store.save_config(cfg)
    print("[OK] Config")

    cv = await mongo_store.get_cv()
    if cv:
        await json_store.save_cv(cv)
        print("[OK] Base CV")
    else:
        print("[SKIP] No base CV found")

    positions = await mongo_store.list_positions()
    for pos in positions:
        await json_store.save_position(pos)
    print(f"[OK] Positions ({len(positions)} migrated)")

    await mongo_store._ensure_connected()
    col = await mongo_store._collection("onboarding_sessions")
    session_count = 0
    async for doc in col.find({}):
        doc.pop("_id", None)
        session = OnboardingSession(**doc)
        await json_store.save_onboarding_session(session)
        session_count += 1
    print(f"[OK] Onboarding sessions ({session_count} migrated)")

    cfg.storage_backend = "json"
    save_app_config(cfg)
    print("\nMigration complete. Storage backend set to 'json'.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate data between JSON files and MongoDB storage"
    )
    parser.add_argument(
        "direction",
        choices=["json-to-mongo", "mongo-to-json"],
        help="Migration direction",
    )
    args = parser.parse_args()

    if args.direction == "json-to-mongo":
        asyncio.run(_json_to_mongo())
    else:
        asyncio.run(_mongo_to_json())


if __name__ == "__main__":
    main()