# github-label-cloner

A simple Python script to clone GitHub Issue Labels from one repository to another.

GitHub Labels are really useful for organising issues and pull requests, especially when you use them with GitHub Projects.    
This script helps you set up new repositories with a ready-made label structure copied from your ideal project.

---

## 🚀 Features

- Copies all labels from one repo to another
- Removes existing labels in target repo by default
- Supports `--keep-existing` flag to preserve existing labels
- Fast and parallel (async, based on `httpx`)
- Uses GitHub API via a personal token

---

## 🔧 Requirements

- Python 3.8+
- [`httpx`](https://www.python-httpx.org/)
- A GitHub personal access token (obtained from [GitHub Settings](https://github.com/settings/tokens))

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 🛠️ Usage

```bash
python copy_labels.py \
  --token YOUR_GITHUB_TOKEN \
  --source username/repo-from \
  --target username/repo-to
```

To **preserve existing labels** in the target repo, use the `--keep-existing` flag:

```bash
python copy_labels.py \
  --token YOUR_GITHUB_TOKEN \
  --source username/repo-from \
  --target username/repo-to \
  --keep-existing
```

You can also provide environment variables instead of flags:

- `GITHUB_TOKEN`
- `SOURCE_REPO`
- `TARGET_REPO`

---

## 🪪 License

This project is licensed under the [MIT Licence](LICENSE).