"""Agent 1 - Repository Inspector: examines metadata, structure and important files."""
from backend import extractor


class RepositoryInspector:
    name = "Repository Inspector"

    def run(self, repo, source: str, display_name: str) -> dict:
        try:
            active = repo.active_branch.name
        except (TypeError, ValueError):
            active = "(detached HEAD)"
        tree = extractor.scan_tree(repo)
        branches = extractor.get_branches(repo)
        return {
            "name": display_name,
            "source": source,
            "remote_url": extractor.remote_url(repo),
            "active_branch": active,
            "total_commits": extractor.total_commit_count(repo),
            "branches": branches,
            "branch_count": len(branches),
            "tag_count": len(repo.tags),
            **tree,
        }
