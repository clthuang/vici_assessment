# Plan: Fix Chrome Launch with Project-Local Profile

## Problem

When Chrome is already running, `launch_system_chrome()` fails because Chrome opens a new window in the existing instance instead of starting with remote debugging enabled.

## Solution

Use a **persistent project-local Chrome profile** at `.chrome-profile/` in the project root. This:
1. Forces Chrome to launch as a new instance (separate from user's normal Chrome)
2. Persists login state between runs (no need to re-login each time)
3. Keeps browser data organized within the project

## Files to Modify

1. `src/subterminator/core/browser.py` - Update `launch_system_chrome()`
2. `.gitignore` - Add `.chrome-profile/`

## Changes

### browser.py

```python
def launch_system_chrome(port: int = 9222) -> str:
    """Launch system Chrome with remote debugging enabled.

    Uses a project-local profile directory (.chrome-profile/) to ensure
    Chrome launches as a new instance even if Chrome is already running.
    The profile persists between runs to preserve login state.
    """
    import urllib.request

    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "google-chrome",  # Linux
        "chrome",  # Linux alternative
    ]

    # Use project-local profile directory for persistence and isolation
    profile_dir = Path.cwd() / ".chrome-profile"
    profile_dir.mkdir(exist_ok=True)

    for path in chrome_paths:
        try:
            subprocess.Popen(
                [
                    path,
                    f"--remote-debugging-port={port}",
                    f"--user-data-dir={profile_dir}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Wait for Chrome to start and verify it's listening
            cdp_url = f"http://localhost:{port}"
            for _ in range(10):  # Try for up to 5 seconds
                time.sleep(0.5)
                try:
                    urllib.request.urlopen(f"{cdp_url}/json/version", timeout=1)
                    return cdp_url
                except Exception:
                    continue

            raise RuntimeError(
                f"Chrome started but not responding on {cdp_url}. "
                "Try closing Chrome windows from .chrome-profile and retry."
            )
        except FileNotFoundError:
            continue

    raise RuntimeError(
        "Could not find Chrome installation. "
        "Use --use-chromium to use Playwright's bundled Chromium instead."
    )
```

### .gitignore

Add:
```
# Chrome profile for subterminator
.chrome-profile/
```

## Key Changes

1. **Project-local profile** at `.chrome-profile/` - forces new Chrome instance, persists login
2. **Verify Chrome is listening** - poll CDP endpoint instead of blind 2-second sleep
3. **Add to .gitignore** - keep browser data out of version control

## Verification

```bash
# With Chrome already running, this should now work:
uv run subterminator cancel --service netflix --verbose

# Should see:
# 1. Chrome launches as separate window (not in existing Chrome)
# 2. Profile stored in .chrome-profile/
# 3. CDP connection succeeds
# 4. If you run again later, login state is preserved
```

## Tests

```bash
uv run pytest tests/ -v --tb=short
```
