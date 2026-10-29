# Notera on your phone

Notera runs as an installable web app (a PWA). It works offline, runs Python in the browser, keeps notes on the phone,
and syncs them with the same private GitHub notes repository your laptop uses. Every time you push an update, the phone gets it
the next time it is opened with internet.

## One-time setup (about 5 minutes)

1. **Turn on the website.** On GitHub open the `NOTERA` repository → *Settings* → *Pages* → *Build and deployment* →
   *Source: GitHub Actions*. The workflow in `.github/workflows/pages.yml` then publishes the app to
   `https://<your-user>.github.io/NOTERA/`. It publishes only the `static/` folder (the app). Your notes are not in that repository.
2. **Open that address on your phone** and install it:
   - Android (Chrome): menu → *Install app* (or *Add to Home screen*).
   - iPhone (Safari): Share → *Add to Home Screen*.
3. **Connect sync.** Tap the status text at the bottom of the sidebar (it says *Saved on this device*). Enter your notes repo as
   `owner/notera-notes` and a token. Create the token at <https://github.com/settings/personal-access-tokens/new>:
   *Only select repositories* → your notes repo, then *Repository permissions → Contents → Read and write*.
   The token is stored only in the phone's browser.

From then on the phone and the laptop merge page by page, newest edit wins, exactly like two laptops do.

## A real APK

The installed web app already behaves like an app. If you want an `.apk` file as well:

1. Go to <https://www.pwabuilder.com>, paste your Pages address, choose *Package for stores → Android* and download the package.
2. Install the `.apk` on the phone (allow installs from your browser or files app once).

This kind of APK is a thin shell that opens your published app, so **it updates itself whenever you push a change**. You never rebuild
it for new features, only if you want to change its name or icon.

## What works on the phone

| | Phone |
|---|---|
| Notes, folders, templates, canvas, stickers, find and replace | yes |
| Python running (`print`, `input()`, errors) | yes, in the browser. The first run downloads Python once (about 10 MB), then it works offline |
| Spaced repetition, flashcards, roadmaps, solve timer | yes |
| Sync with GitHub | yes |
| Export a backup `.json` for the laptop (or just sync) | yes |
| Recently deleted | yes |
| Snapshots / history browser | laptop only |
| AI assistant, fetching a problem from its LeetCode link | laptop only (the browser cannot call those services directly) |
| Sharing with a friend over the relay | laptop only |

## Moving notes between phone and laptop

- **Easiest:** sync. Both devices read and write the same `pages.json` in your private repo.
- **Without GitHub:** on the phone use *⋯ → Export*, send the file to the laptop, and on the laptop use *⋯ → Import*.

## Developing

`python tests/test_standalone.py` checks phone mode end to end with a fake GitHub (storage, export, sync both ways, Python, install files).
