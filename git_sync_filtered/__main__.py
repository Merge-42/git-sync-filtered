#!/usr/bin/env python3
"""
git-sync-filtered - Sync filtered commits from private to public repo

Usage:
    git-sync-filtered --private /path/to/private --public /path/to/public --keep src --keep docs
"""

from git_sync_filtered.cli import main

if __name__ == "__main__":
    main()
