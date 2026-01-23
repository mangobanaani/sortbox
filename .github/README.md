# GitHub Actions CI/CD

## Workflows

### CI (`ci.yml`)

Runs on:
- Manual trigger (workflow_dispatch)
- Push to main or feature/* branches
- Pull requests to main

**Jobs:**
1. **Test** - Run pytest with coverage (target: 80%)
2. **Lint** - Run ruff check and format verification
3. **Type Check** - Run mypy strict mode
4. **Security** - Run bandit and safety scans
5. **Build** - Build Docker image (no push)

### CD (`cd.yml`)

**Manual trigger only** with environment selection (staging/production).

Builds and pushes Docker image to Docker Hub.

## Secrets Required

- `CODECOV_TOKEN` - For coverage reporting
- `DOCKERHUB_USERNAME` - Docker Hub username
- `DOCKERHUB_TOKEN` - Docker Hub access token

## Local Testing

Run the same checks locally:

```bash
make check  # Runs lint, typecheck, security, test
```
