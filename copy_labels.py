#!/usr/bin/env python3
import argparse
import asyncio
import logging
import os
import sys
from typing import Dict, List
from urllib.parse import quote

import httpx

BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'
RESET = '\033[0m'

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': CYAN,
        'INFO': GREEN,
        'WARNING': YELLOW,
        'ERROR': RED,
        'CRITICAL': RED,
    }

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}[{levelname}]{RESET}"
        return super().format(record)

# Logging
handler = logging.StreamHandler()
formatter = ColoredFormatter('%(levelname)s %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

class GitHubLabelManager:
    def __init__(self, token: str):
        if not token:
            raise ValueError("GitHub token is required.")
        self.token = token
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        self.base_url = "https://api.github.com"

    async def check_repo_exists(self, client: httpx.AsyncClient, repo: str) -> bool:
        url = f"{self.base_url}/repos/{repo}"
        try:
            r = await client.get(url, headers=self.headers)
            if r.status_code == 200:
                return True
            elif r.status_code == 404:
                logger.error(f"❌ Repository '{repo}' not found (404)")
            else:
                logger.error(f"❌ Failed to check repository '{repo}': {r.status_code} {r.text}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"Error checking repository '{repo}': {e}")
            return False

    async def get_labels(self, client: httpx.AsyncClient, repo: str) -> List[Dict]:
        url = f"{self.base_url}/repos/{repo}/labels"
        labels = []
        page = 1

        while True:
            params = {"per_page": 100, "page": page}
            try:
                r = await client.get(url, headers=self.headers, params=params)
                r.raise_for_status()
                page_data = r.json()
                if not page_data:
                    break
                labels.extend(page_data)
                if len(page_data) < 100:
                    break
                page += 1
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch labels from {repo}: {e}")
                break

        return labels

    async def delete_label(self, client: httpx.AsyncClient, repo: str, label_name: str) -> None:
        url = f"{self.base_url}/repos/{repo}/labels/{quote(label_name, safe='')}"
        try:
            r = await client.delete(url, headers=self.headers)
            if r.status_code == 204:
                logger.info(f"🗑️ Deleted label '{label_name}' from '{repo}'")
            else:
                logger.warning(f"⚠️ Failed to delete label '{label_name}': {r.status_code} {r.text}")
        except httpx.HTTPError as e:
            logger.error(f"Error deleting label '{label_name}': {e}")

    async def create_label(self, client: httpx.AsyncClient, repo: str, label: Dict) -> None:
        url = f"{self.base_url}/repos/{repo}/labels"
        payload = {
            "name": label["name"],
            "color": label["color"],
            "description": label.get("description", "")
        }
        try:
            r = await client.post(url, headers=self.headers, json=payload)
            if r.status_code == 201:
                logger.info(f"✅ Created label '{label['name']}' in '{repo}'")
            elif r.status_code == 422:
                logger.warning(f"⚠️ Label '{label['name']}' already exists in '{repo}'")
            else:
                logger.error(f"❌ Failed to create label '{label['name']}': {r.status_code} {r.text}")
        except httpx.HTTPError as e:
            logger.error(f"Error creating label '{label['name']}': {e}")

    async def clear_labels(self, client: httpx.AsyncClient, repo: str) -> None:
        logger.info(f"🧼 Clearing existing labels from '{repo}'")
        labels = await self.get_labels(client, repo)
        tasks = [self.delete_label(client, repo, label["name"]) for label in labels]
        await asyncio.gather(*tasks)

    async def copy_labels(self, from_repo: str, to_repo: str, clear_existing: bool = True):
        async with httpx.AsyncClient(timeout=30) as client:
            if clear_existing:
                await self.clear_labels(client, to_repo)

            logger.info(f"📥 Copying labels from '{from_repo}' to '{to_repo}'")
            labels = await self.get_labels(client, from_repo)
            if not labels:
                logger.warning(f"No labels found in source repository '{from_repo}'")
                return

            logger.info(f"Found {len(labels)} labels to copy")
            tasks = [self.create_label(client, to_repo, label) for label in labels]
            await asyncio.gather(*tasks)


async def main():
    parser = argparse.ArgumentParser(description="Copy GitHub labels between repositories")
    parser.add_argument("--source", "-s", help="Source repository (username/repo)")
    parser.add_argument("--target", "-t", help="Target repository (username/repo)")
    parser.add_argument("--token", help="GitHub token or GITHUB_TOKEN env var")
    parser.add_argument("--keep-existing", action="store_true", help="Keep existing labels in target")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITHUB_TOKEN")
    source = args.source or os.environ.get("SOURCE_REPO")
    target = args.target or os.environ.get("TARGET_REPO")

    if not token or not source or not target:
        logger.error("Missing required arguments --token, --source, or --target")
        sys.exit(1)

    manager = GitHubLabelManager(token)

    async with httpx.AsyncClient(timeout=30) as client:
        source_exists = await manager.check_repo_exists(client, source)
        target_exists = await manager.check_repo_exists(client, target)

    if not source_exists or not target_exists:
        logger.error("🚫 Aborting due to missing repository.")
        sys.exit(1)

    await manager.copy_labels(source, target, clear_existing=not args.keep_existing)

    logger.info("✅ Done!")

if __name__ == "__main__":
    asyncio.run(main())