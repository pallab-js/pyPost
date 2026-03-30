import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class GitStatus:
    is_repo: bool
    is_dirty: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    current_branch: Optional[str] = None


@dataclass
class GitCommit:
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    files_changed: List[str]


class GitManager:
    """Git operations for collection versioning"""

    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path) if repo_path else self._get_default_repo_path()
        self._ensure_repo()

    def _get_default_repo_path(self) -> Path:
        home = Path.home()
        return home / '.pypost' / 'collections'

    def _ensure_repo(self):
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        git_dir = self.repo_path / '.git'
        if not git_dir.exists():
            self._run_git(['init'])
            self._create_gitignore()
            logging.info(f"Initialized Git repository at {self.repo_path}")

    def _create_gitignore(self):
        gitignore_path = self.repo_path / '.gitignore'
        if not gitignore_path.exists():
            content = """# pyPost files to ignore in version control
*.db
.encryption_key
*.log
__pycache__/
*.pyc
.idea/
.vscode/
*.egg-info/
dist/
build/
"""
            with open(gitignore_path, 'w') as f:
                f.write(content)

    def _run_git(self, args: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        try:
            result = subprocess.run(
                ['git'] + args,
                cwd=str(self.repo_path),
                capture_output=capture_output,
                text=True,
                check=False
            )
            if result.returncode != 0 and capture_output:
                logging.warning(f"Git command failed: {' '.join(args)} - {result.stderr}")
            return result
        except FileNotFoundError:
            raise RuntimeError("Git is not installed. Please install Git to use version control features.")

    def is_repo(self) -> bool:
        git_dir = self.repo_path / '.git'
        return git_dir.exists() and git_dir.is_dir()

    def status(self) -> GitStatus:
        if not self.is_repo():
            return GitStatus(is_repo=False, is_dirty=False, staged_files=[], 
                           unstaged_files=[], untracked_files=[])

        result = self._run_git(['status', '--porcelain=v1'])
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        staged = []
        unstaged = []
        untracked = []
        
        for line in lines:
            if len(line) < 2:
                continue
            
            index_status = line[0]
            worktree_status = line[1]
            filepath = line[3:].strip()
            
            if index_status == '?' and worktree_status == '?':
                untracked.append(filepath)
            elif index_status in ['M', 'A', 'D', 'R', 'C']:
                staged.append(filepath)
            else:
                unstaged.append(filepath)

        branch_result = self._run_git(['branch', '--show-current'])
        current_branch = branch_result.stdout.strip() or 'HEAD'

        return GitStatus(
            is_repo=True,
            is_dirty=len(lines) > 0,
            staged_files=staged,
            unstaged_files=unstaged,
            untracked_files=untracked,
            current_branch=current_branch
        )

    def diff(self, file_path: Optional[str] = None) -> str:
        args = ['diff']
        if file_path:
            args.append('--', file_path)
        
        result = self._run_git(args)
        return result.stdout

    def diff_staged(self, file_path: Optional[str] = None) -> str:
        args = ['diff', '--cached']
        if file_path:
            args.append('--', file_path)
        
        result = self._run_git(args)
        return result.stdout

    def add(self, files: List[str]) -> bool:
        if not files:
            return True
        
        result = self._run_git(['add'] + files)
        return result.returncode == 0

    def add_all(self) -> bool:
        result = self._run_git(['add', '-A'])
        return result.returncode == 0

    def commit(self, message: str) -> Optional[str]:
        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty")
        
        result = self._run_git(['commit', '-m', message])
        if result.returncode == 0:
            return self.get_latest_commit_hash()
        return None

    def log(self, max_count: int = 50) -> List[GitCommit]:
        result = self._run_git(['log', f'--max-count={max_count}', '--pretty=format:%H|%h|%s|%an|%ai|%d'])
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 5:
                commit = GitCommit(
                    hash=parts[0],
                    short_hash=parts[1],
                    message=parts[2],
                    author=parts[3],
                    date=parts[4],
                    files_changed=[]
                )
                commits.append(commit)
        
        return commits

    def get_latest_commit_hash(self) -> Optional[str]:
        result = self._run_git(['rev-parse', 'HEAD'])
        return result.stdout.strip() if result.returncode == 0 else None

    def get_file_at_commit(self, file_path: str, commit: Optional[str] = None) -> Optional[str]:
        args = ['show']
        if commit:
            args.append(commit + ':' + file_path)
        else:
            args.append('HEAD:' + file_path)
        
        result = self._run_git(args)
        return result.stdout if result.returncode == 0 else None

    def checkout(self, ref: str, create_branch: bool = False, branch_name: Optional[str] = None) -> bool:
        args = ['checkout']
        
        if create_branch:
            args.append('-b')
            if branch_name:
                args.append(branch_name)
        
        args.append(ref)
        
        result = self._run_git(args)
        return result.returncode == 0

    def create_branch(self, branch_name: str) -> bool:
        result = self._run_git(['branch', branch_name])
        return result.returncode == 0

    def delete_branch(self, branch_name: str, force: bool = False) -> bool:
        args = ['branch']
        if force:
            args.append('-D')
        else:
            args.append('-d')
        args.append(branch_name)
        
        result = self._run_git(args)
        return result.returncode == 0

    def list_branches(self) -> List[str]:
        result = self._run_git(['branch', '-a'])
        branches = []
        
        for line in result.stdout.strip().split('\n'):
            branch = line.strip()
            if branch.startswith('* '):
                branch = branch[2:]
            if branch:
                branches.append(branch)
        
        return branches

    def get_current_branch(self) -> str:
        result = self._run_git(['branch', '--show-current'])
        return result.stdout.strip() or 'HEAD'

    def restore(self, file_path: str, from_ref: Optional[str] = None) -> bool:
        args = ['restore']
        if from_ref:
            args.extend([from_ref, '--', file_path])
        else:
            args.extend(['--', file_path])
        
        result = self._run_git(args)
        return result.returncode == 0

    def reset(self, ref: str, hard: bool = False) -> bool:
        args = ['reset']
        if hard:
            args.append('--hard')
        args.append(ref)
        
        result = self._run_git(args)
        return result.returncode == 0

    def get_file_history(self, file_path: str) -> List[Dict]:
        result = self._run_git(['log', '--follow', '--pretty=format:%H|%h|%s|%an|%ai', '--', file_path])
        
        history = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 5:
                history.append({
                    'hash': parts[0],
                    'short_hash': parts[1],
                    'message': parts[2],
                    'author': parts[3],
                    'date': parts[4]
                })
        
        return history

    def save_collections_to_files(self, collections: List[Dict]):
        collections_dir = self.repo_path / 'collections'
        collections_dir.mkdir(exist_ok=True)
        
        for collection in collections:
            name = collection.get('name', 'unnamed').replace('/', '_').replace('\\', '_')
            file_path = collections_dir / f"{name}.json"
            
            with open(file_path, 'w') as f:
                json.dump(collection, f, indent=2)

    def load_collections_from_files(self) -> List[Dict]:
        collections_dir = self.repo_path / 'collections'
        collections = []
        
        if not collections_dir.exists():
            return collections
        
        for file_path in collections_dir.glob('*.json'):
            try:
                with open(file_path) as f:
                    collection = json.load(f)
                    collections.append(collection)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load collection from {file_path}: {e}")
        
        return collections

    def stash(self, message: Optional[str] = None) -> bool:
        args = ['stash']
        if message:
            args.extend(['push', '-m', message])
        else:
            args.append('push')
        
        result = self._run_git(args)
        return result.returncode == 0

    def stash_pop(self) -> bool:
        result = self._run_git(['stash', 'pop'])
        return result.returncode == 0

    def stash_list(self) -> List[Dict]:
        result = self._run_git(['stash', 'list', '--pretty=format:%H|%gd|%s'])
        
        stashes = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('|')
            if len(parts) >= 3:
                stashes.append({
                    'hash': parts[0],
                    'ref': parts[1],
                    'message': parts[2]
                })
        
        return stashes
