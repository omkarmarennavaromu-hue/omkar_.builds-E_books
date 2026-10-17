# omkar_.builds-E_books — published on GitHub Pages

- **Live site:** https://omkarmarennavaromu-hue.github.io/omkar_.builds-E_books/
- **Public repository:** https://github.com/omkarmarennavaromu-hue/omkar_.builds-E_books
- **Publishing source:** GitHub Actions workflow `.github/workflows/pages.yml`, deploying only `docs/` from the `main` branch.

The public site was deployed and checked for successful responses from its homepage, full online reader, PDF and EPUB downloads, film, styles and scripts. Subsequent pushes that change `docs/` or the workflow automatically redeploy the site; you can also run the workflow manually from the repository's Actions tab.

## What is and isn't hosted

The `docs/` directory is a self-contained static edition. It includes the complete HTML e-book reader, PDF and EPUB files, cover, page previews, fonts and original 20-second film. Relative asset paths make it work at the project URL above.

**GitHub Pages cannot run the Python/SQLite feedback API.** The hosted edition does not display non-working rating/review controls or made-up results. The full feedback-enabled server edition remains in `public/` plus `server.py` for a future host with persistent storage. `/admin` is not published on GitHub Pages.

## Updating the live site

From an authenticated local clone of the public repository, after changing the site:

```bash
python tools/export_pages.py
python tests/smoke.py
git add public docs tools README.md PUBLISH.md .github/workflows/pages.yml
git commit -m "Update e-book site"
git push origin main
```

If you update only the documentation, it will appear in the repository without redeploying the website; the workflow runs on changes to `docs/` or `.github/workflows/pages.yml`. `tools/build_reader.py` regenerates the complete reader only when the canonical manuscript in the sibling e-book project is available; the already-built `public/reader.html` is included in this repository. `tests/smoke.py` tests the feedback-enabled server in an isolated temporary database and does not create sample feedback in the live database.

## Security

Never commit the private `data/admin_access.txt`, `data/visitor_signing.key`, or `data/feedback.sqlite3` files; they are excluded from Git. If any access token has ever been shared, revoke it in GitHub Settings → Developer settings → Personal access tokens. Authenticate through a secure browser/device or trusted SSH flow rather than putting a token in a chat, repository, URL or shell history. No custom domain is configured.
