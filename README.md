# git-sync-filtered

![GitHub Repo stars](https://img.shields.io/github/stars/Merge-42/git-sync-filtered?style=social)
![Python versions](https://img.shields.io/pypi/pyversions/git-sync-filtered)
![License](https://img.shields.io/pypi/l/git-sync-filtered)

A thin wrapper around [git-filter-repo](https://github.com/newren/git-filter-repo) for syncing filtered commits from a private repository to a public repository.

## Overview

git-sync-filtered clones a private repository, filters it to only include specified paths using git-filter-repo, and pushes the result to a public repository's sync branch. This enables maintaining a public subset of a private repository while preserving commit history.

## Installation

### uv (recommended)

```bash
uv tool install git+https://github.com/Merge-42/git-sync-filtered
```

### uvx (run without installing)

```bash
uvx git+https://github.com/Merge-42/git-sync-filtered \
  --private git@github.com:org/private.git \
  --public git@github.com:org/public.git \
  --keep src \
  --keep docs
```

### pip

```bash
pip install git+https://github.com/Merge-42/git-sync-filtered
```

## Usage

```bash
git-sync-filtered \
  --private git@github.com:org/private.git \
  --public git@github.com:org/public.git \
  --keep src \
  --keep docs
```

### Using a paths file

Create a file with paths to keep (one per line, lines starting with `#` are comments):

```text
src
docs
README.md
```

```bash
git-sync-filtered \
  --private git@github.com:org/private.git \
  --public git@github.com:org/public.git \
  --keep-from-file paths.txt
```

## Options

| Option             | Description                                   | Default         |
| ------------------ | --------------------------------------------- | --------------- |
| `--private`        | Private repo path or URL                      | Required        |
| `--public`         | Public repo path or URL                       | Required        |
| `--keep`           | Paths to keep (specify multiple)              | Required        |
| `--keep-from-file` | File containing paths to keep                 | -               |
| `--sync-branch`    | Sync branch name                              | `upstream/sync` |
| `--main-branch`    | Main branch name                              | `main`          |
| `--private-branch` | Private branch to sync from                   | `main`          |
| `--dry-run`        | Show what would happen without making changes | `false`         |
| `--merge`          | Merge into main branch after sync             | `false`         |
| `--force`          | Force push                                    | `false`         |

## How It Works

1. Clones the private repository
2. Runs git-filter-repo to filter to only the specified paths
3. Pushes filtered commits to the public repository's sync branch
4. Optionally merges the sync branch into main

The sync branch can then be merged into main manually or with `--merge`.

## Workflow

```mermaid
flowchart LR
    A[Private Repo<br/>private-branch] -->|clone & filter| B[git-sync-filtered]
    B -->|push| C[Public Repo<br/>sync-branch]
    C -->|"merge<br/>(manual or with --merge)"| D[Public Repo<br/>main-branch]
```

## Requirements

- Python 3.10+
- git >= 2.36.0

---

Sponsored by [Merge 42](https://merge42.com)
