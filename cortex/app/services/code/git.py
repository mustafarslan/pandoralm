"""
Git Repository Service
Handles cloning and managing git repositories for the Code Brain.
"""
import os
import shutil
import tempfile
import logging
import git
from typing import Generator, Optional

logger = logging.getLogger(__name__)

class GitRepository:
    """
    Context manager for cloning and cleaning up git repositories.
    """
    def __init__(self, repo_url: str, branch: Optional[str] = None):
        self.repo_url = repo_url
        self.branch = branch
        self.temp_dir = tempfile.mkdtemp(prefix="pandora_git_")
        self.repo_path = os.path.join(self.temp_dir, "repo")

    def __enter__(self):
        """Clone the repository."""
        logger.info(f"Cloning {self.repo_url} to {self.repo_path}")
        try:
            options = ["--depth=1"]
            if self.branch:
                options.append(f"--branch={self.branch}")
            
            git.Repo.clone_from(self.repo_url, self.repo_path, multi_options=options)
            return self.repo_path
        except Exception as e:
            logger.error(f"Failed to clone {self.repo_url}: {e}")
            self._cleanup()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup temporary directory."""
        self._cleanup()

    def _cleanup(self):
        if os.path.exists(self.temp_dir):
            logger.info(f"Cleaning up {self.temp_dir}")
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Basic validation for git URLs."""
        # Add more robust checks if needed (e.g. check for .git extension or specific domains)
        return url.startswith("http://") or url.startswith("https://") or url.startswith("git@")
