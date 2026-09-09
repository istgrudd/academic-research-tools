# Security Policy

## Supported versions

Until a stable release, only the latest `0.2.x` release receives security fixes.

## Reporting a vulnerability

Please do not open a public issue for credential exposure, command execution, dependency confusion, path traversal, or another exploitable vulnerability.

Prefer a private GitHub Security Advisory:

1. open the repository's **Security** tab
2. select **Report a vulnerability**
3. include affected version, reproduction steps, impact, and a suggested mitigation if known

If private reporting is unavailable, contact `digitalrudi14@gmail.com` with the subject `Academic Research Tools security report`. Do not include real API keys or provider data in the initial message.

## Credential model

Academic Research Tools is local-first:

- provider credentials are resolved from environment variables or a protected per-user configuration file
- credentials are not accepted as CLI arguments
- interactive credential input uses a hidden terminal prompt and refuses non-interactive input
- user configuration is written with directory mode `0700` and file mode `0600` on Unix
- insecure credential file and directory permissions are rejected on Unix
- `status` and `doctor` report availability and source only, never values
- no telemetry is implemented
- provider responses are returned to the caller and are not automatically persisted
- MCP v0.2 uses local stdio transport rather than a hosted credential-custody service

The protected JSON file is plaintext and is not an encrypted vault or operating-system keyring. `.env` files are ignored by Git and `.env.example` contains empty values only. Users remain responsible for shell history, process environment, MCP host configuration, backups, local account security, and provider account security.

## Safe disclosure and rotation

If a credential may have been exposed:

1. revoke or rotate it with the provider immediately
2. remove it from current files and runtime configuration
3. if committed, rewrite repository history where appropriate
4. invalidate cached CI artifacts or logs that contained it
5. notify affected collaborators privately

Deleting only the latest Git commit is not sufficient after a secret has been pushed.

## Provider and data security boundaries

The MIT license covers this source code, not provider data. This project does not grant access beyond a user's API key, subscription, or institutional network entitlement. Vulnerabilities in Elsevier, Semantic Scholar, arXiv, Google, SerpAPI, an MCP host, or another dependency should also be reported to the responsible vendor.

Do not submit vulnerability reports containing large copyrighted API responses, unpublished papers, personal data, or third-party credentials.
