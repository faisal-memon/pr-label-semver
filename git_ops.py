from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from errors import ActionError

if TYPE_CHECKING:
    from config import GitHubConfig


class Git:
    """Wrapper for git and GitHub operations used by the action."""

    def list_tags(self) -> list[str]:
        """Return tags sorted newest-first after refreshing remote tags."""
        self.run("fetch", "--tags", "--force", check=False, capture_output=True)
        result = self.run(
            "tag",
            "-l",
            "--sort=-version:refname",
            capture_output=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def get_pull_request_labels(self, github: GitHubConfig) -> tuple[int, list[str]] | None:
        """Return the matching PR number and labels for the target branch, if any."""
        pulls = self.get_associated_pull_requests(github)
        selected_pr = next((pull for pull in pulls if pull.get("base", {}).get("ref") == github.target_branch), None)
        if selected_pr is None:
            return None

        pr_number = selected_pr.get("number")
        labels = [label.get("name", "") for label in selected_pr.get("labels", [])]
        return pr_number, labels

    def get_associated_pull_requests(self, github: GitHubConfig) -> list[dict]:
        """Fetch pull requests associated with the configured commit SHA."""
        owner, repo = github.repository.split("/", 1)
        request = urllib.request.Request(
            url=f"{github.api_url}/repos/{owner}/{repo}/commits/{github.sha}/pulls",
            headers={
                "Authorization": f"Bearer {github.token}",
                "Accept": "application/vnd.github+json",
            },
        )

        try:
            with urllib.request.urlopen(request) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise ActionError(f"Failed to query pull requests for commit {github.sha}: HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ActionError(f"Failed to query pull requests for commit {github.sha}: {exc.reason}.") from exc

    def run(
        self,
        *args: str,
        capture_output: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command and return the completed process."""
        return subprocess.run(
            ["git", *args],
            check=check,
            text=True,
            capture_output=capture_output,
        )
