# Publish `omkar_.builds-E_books` (public GitHub Pages repository)

## First: secure your GitHub account

A personal access token was shared in chat. **Revoke that token in GitHub Settings → Developer settings → Personal access tokens** and do not put a replacement in a chat message, repository, ZIP, URL, or command history. Authenticate on your own computer with the GitHub CLI's interactive `gh auth login` flow (or a trusted local SSH setup).

The project deliberately excludes `data/admin_access.txt`, `data/visitor_signing.key`, and `data/feedback.sqlite3` from Git and from the downloadable ZIP. Check `git status` before publishing; none of those files should appear.

## What GitHub Pages will publish

The `docs/` directory is a self-contained **static edition**. It includes the complete HTML e-book reader, PDF and EPUB files, cover, page previews, fonts, and original 20-second film. All local asset paths are relative, so the site works at the project URL `https://<your-username>.github.io/omkar_.builds-E_books/`.

**GitHub Pages cannot run the Python/SQLite feedback API.** This hosted edition does not present non-working rating/review controls or made-up results. The full server-backed version remains in `public/` plus `server.py` for a later host with persistent storage. `/admin` is not part of the Pages edition.

## Create the public repository and push

On your own computer, unzip the project and install/authenticate [GitHub CLI](https://cli.github.com/) if needed. Then run these commands inside the extracted `omkar_builds_ebooks` directory:

```bash
gh auth login
git init -b main
git add .
git status --short
git commit -m "Launch omkar_.builds e-book library"
gh repo create 'omkar_.builds-E_books' --public --source=. --remote=origin --push
```

If the repository already exists in your account, use `git remote add origin https://github.com/<your-username>/omkar_.builds-E_books.git` and `git push -u origin main` instead of `gh repo create`.

## Turn on Pages

In the GitHub repository, open **Settings → Pages** and select **GitHub Actions** as the build/deployment source. The workflow in `.github/workflows/pages.yml` uploads **only `docs/`** and deploys it. If the first workflow ran before Pages was enabled, open **Actions → Publish e-book website to GitHub Pages → Run workflow**. The deployment URL appears on the Pages settings screen and in the workflow's `github-pages` environment.

No custom domain is configured; you can add one later in Settings → Pages.

## Updating the static site

After changing the public site, rebuild the Pages edition and push:

```bash
python tools/export_pages.py
git add public docs tools README.md PUBLISH.md .github/workflows/pages.yml
git commit -m "Update e-book site"
git push
```

`tools/build_reader.py` regenerates the complete reader only when the canonical manuscript in the sibling e-book project is available; the already-built `public/reader.html` is included in this package. `python tests/smoke.py` tests the full server in an isolated temporary database and does not create sample feedback in your live data.
