# docker-praveen: Run Browser-Use in Docker with many LLM keys

This guide explains how to use `docker-praveen.ps1` to run the `browseruse` container with multiple provider API keys and how to resolve the build error you encountered.

## Prerequisites
- Docker Desktop installed
- Image built (see Build section)
- PowerShell (run from repo root)

## Build
You started with:

```powershell
docker build -t browseruse .
```

If you hit a Playwright Chromium dependency error similar to:

```
E: Package 'ttf-unifont' has no installation candidate
E: Package 'ttf-ubuntu-font-family' has no installation candidate
Failed to install browsers
```

Use one of these fixes:

### Option A: Fast build path (recommended)
Build the precomposed base images and then the fast Dockerfile:

```bash
./docker/build-base-images.sh
```

Then:

```powershell
docker build -f Dockerfile.fast -t browseruse .
```

### Option B: Stick with standard Dockerfile and add fonts
If you must use `Dockerfile`, add Debian font packages before the Playwright install step, or switch Playwright to avoid the deprecated `ttf-*` packages. The fast path above avoids this on most systems.

## Configure keys
Create a `.env` file in the repo root (next to this script) with any keys you have:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_KEY=...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
GROQ_API_KEY=...
GROK_API_KEY=...
NOVITA_API_KEY=...
BROWSERBASE_API_KEY=...
POSTHOG_API_KEY=...
POSTHOG_HOST=...
```

You can also export them in your current PowerShell session; `.env` values take precedence.

## Run
Use the provided PowerShell helper script:

```powershell
# from repo root
./docker-praveen.ps1
```

- It reads `.env` and prompts for any missing keys (use `-NoPrompt` to skip prompts).
- It mounts `./data` to `/data` in the container and sets `--shm-size 2g`.

Common flags:

```powershell
./docker-praveen.ps1 -ImageName browseruse -DataDir "${PWD}\data" -ShmSize "2g" -NoPrompt
```

## Why this works
- `docker-praveen.ps1` centralizes all `-e KEY=...` flags so you don't have to repeat long commands.
- The fast build uses pre-built layers to avoid brittle Playwright dependency resolution during each app build.

## Troubleshooting
- If Chromium crashes, ensure `--shm-size=2g` is set.
- If the container can’t reach your APIs, confirm keys are present inside the container:

```powershell
docker run --rm browseruse env | Select-String OPENAI
```

- If the fast build can’t pull `browseruse/base-*` locally, ensure you ran `./docker/build-base-images.sh` from a Unix-like shell (Git Bash/WSL). Alternatively, manually build each base image using `docker buildx` in `docker/base-images/*`.

## Next steps
Run the container and follow the interactive CLI to start tasks, or pass any additional CLI args you use in your workflow by editing `docker-praveen.ps1`.
