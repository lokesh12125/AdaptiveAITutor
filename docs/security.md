# Security and privacy

## Execution isolation

Student code is untrusted. The execution service is a separate process, reachable only with a shared token, and each job gets a new container:

| Control | Setting |
|---|---|
| Network | `--network none` |
| Filesystem | `--read-only`, with a 32 MB `noexec` temp area |
| User | 65534, unprivileged |
| Capabilities | All dropped, with `no-new-privileges` |
| Memory | 256 MB for the container, with no swap, and 192 MB per test process |
| Processes | 64 at most |
| CPU | 1 core |
| Time | Per test (default 2 seconds), per job, and a hard limit with `docker kill` |
| Output | 64 KB per test |
| Cleanup | `--rm`, and each test's processes are killed |
| Supervisor | Runs as PID 1 and is not dumpable, so student processes cannot signal it or read its memory |
| Answers | Never enter the container |

`runner/tests/test_isolation.py` attempts each abuse from inside the sandbox on this machine.

### Limits you should know

- **Not production-audited.** These tests show the controls work here. They are not a security audit. Containers share a kernel, so a kernel exploit could escape. For hostile public use, add gVisor or Firecracker and a dedicated host.
- **The Docker socket.** In the full Compose stack, the execution service mounts `/var/run/docker.sock`, which is equivalent to root on the host if that service were compromised. It never runs student code itself, and it has no published port, but it does run as root in its container to use the socket. A socket proxy or a dedicated VM is better for real deployment.
- **Docker Desktop on macOS** runs containers in a VM, which helps, but tests here do not cover Linux hosts.
- **`RUNNER_BACKEND=local_dev_unsafe`** is an explicit opt-in for machines without Docker. It uses a macOS sandbox profile that blocks network, writes and reading your home folder, but has no memory or process limits, and no sandbox at all on other systems. The UI shows a warning banner, and Docker failure never switches to it automatically.

## Application security

| Area | Implementation |
|---|---|
| Passwords | Argon2id |
| Sessions | Random token, stored hashed, in an HttpOnly SameSite=Lax cookie. Secure in production. Revocable. |
| Authorisation | Checked on the server for every request. Learners reach only their own records. Teachers reach only their own classes, and only learners who joined. |
| Roles | A teacher needs an invite code. There is no default code: empty disables teacher sign-up. |
| CSRF | SameSite=Lax, and writes must be JSON |
| Abuse | Rate limits on auth, Run, Submit, Hint and imports. Size limits on code and requests. |
| Hidden data | Hidden test contents and reference solutions are never sent to clients. Tests check this. |
| Model safety | Learner text is delimited as data. The validator checks all output. |
| Imported text | Rendered with raw HTML disabled |
| Errors | Structured, with a correlation ID, and no stack traces to clients |
| Secrets | From the environment. `.env` is ignored by Git. |

**Production settings:** with `ENVIRONMENT=production`, the API refuses to start if demo mode or synthetic retrieval is on, the runner token is weak, or the database uses the development password. It also turns off API docs and traces, and marks cookies Secure.

**Limitations:** rate limits are per process and in memory. There is no email verification or password reset. Multi-factor sign-in is not implemented. Demo access creates unauthenticated throwaway accounts: set `DEMO_MODE=false` for anything real.

## Action needed on the earlier repository

`backend/.auth_secret`, the earlier app's token signing key, is **committed in Git history and the `origin` remote**. It is removed on this branch, and the new app does not use it, but it stays in history. If the earlier app was ever deployed, treat that key as compromised. Removing it from history requires rewriting history, which is your decision, so I did not do it. `backend/.env` was never committed.

## Privacy

| Stored | Not stored |
|---|---|
| Account, code you run or submit, drafts | Keystroke content or the timing of individual keys |
| Results, hints, estimates, answers you give | Anything from other sites or your device |
| Active seconds per problem, counted while the page is visible and you are active | |

No teacher can see a learner's data until that learner joins their class.

- **Pooled outcomes:** resolved hints may be stored anonymously: level, strategy, issue, topic, outcome and situation vector, with a one-way owner hash used only to exclude your own cases. There is no name, code or problem text. Learners can opt out in Settings, and demo accounts are never pooled.
- **Research use** is opt-in and separate.
- **Data controls:** download everything, delete your account. Deleting removes your linked records. Pooled anonymous cases stay, since they cannot be traced to you, though the owner hash could be matched by someone holding your user ID and database access.
- **Model providers:** when one is enabled, the task, your code and your message are sent to it. Nothing else about you is. Check that provider's data policy before using it with real students.
- **Before a real study:** get approval through your institution, use a consent form, set a retention period, and set `DEMO_MODE=false`.
