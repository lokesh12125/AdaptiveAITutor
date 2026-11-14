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

### Tracing and lesson examples

To answer a question, the tutor can run the learner's code again with a tracer that records local variables on the lines they pointed at. This runs inside the same sandbox with the same limits. It uses visible tests only, so hidden inputs and answers are never traced or shown. It records at most 40 events, 12 variables per event and 80 characters per value, and it never decides a test result. Lesson examples run through the same execution path, with the same limits and rate limit as Run.

### Edited and added test cases

When a learner edits or adds a test case, each value is read with `ast.literal_eval`, so only plain values (numbers, text, lists, dictionaries, True, False, None) are accepted, never code. The learner's code and the reference solution then run on that input in separate sandbox jobs with the usual limits. Only the reference's answer is shown, as the expected value. Its code never leaves the server. This gives the learner an oracle for inputs they choose, as most coding sites do. It does not reveal hidden tests, whose inputs the learner never sees.

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
| Imported web pages | Scripts, styles and hidden elements are removed before parsing, so hidden text cannot carry instructions. The learner reviews everything before saving, and model prompts treat the task as data. |
| Link import (SSRF) | See "Opening external links" below |
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

- **Profile:** learners see their own profile. A teacher sees the same profile only for students in their own class. The situation vector and the last similar-situation match appear as numbers and counts. Other learners' names, ids, code and answers are never part of it, and the backend test checks that the match block holds only counts, rates and the strategy name.

- **Pooled outcomes:** resolved hints may be stored anonymously: level, strategy, issue, topic, outcome and situation vector, with a one-way owner hash used only to exclude your own cases. There is no name, code or problem text. Learners can opt out in Settings, and demo accounts are never pooled.
- **Research use** is opt-in and separate.
- **Data controls:** download everything, delete your account. Deleting removes your linked records. Pooled anonymous cases stay, since they cannot be traced to you, though the owner hash could be matched by someone holding your user ID and database access.
- **Model providers:** when one is enabled, the task, your code and your message are sent to it. Nothing else about you is. Check that provider's data policy before using it with real students.
- **Before a real study:** get approval through your institution, use a consent form, set a retention period, and set `DEMO_MODE=false`.

## Opening external links

Add Question can fetch a page at a learner's request, which makes the server a possible route into private networks. It is limited as follows, in `imports/fetcher.py`:

| Control | Detail |
|---|---|
| Address checks | http and https only, standard ports only, no credentials, no raw IP addresses, no bare or internal hostnames |
| Resolved addresses | Every address a name resolves to must be public. One private address among several refuses the request. |
| DNS rebinding | The connection goes to the address that was checked, with the original name used for `Host` and TLS |
| Redirects | At most 3, and each is checked from the start, including robots.txt at the destination |
| Limits | 12 seconds in total, 2 MB after decompression, web pages and plain text only |
| Politeness | robots.txt with RFC 9309 matching, Crawl-delay, Content-Signal `ai-input=no`, `noai` markers, spacing per host, caching |
| Operators | `IMPORT_PAGE_FETCH=false` turns it off, and `IMPORT_BLOCKED_DOMAINS` lists domains never to open |

Tested with simulated network responses in `backend/tests/test_link_import.py`, including private ranges, IPv4-mapped IPv6, mixed answers, and redirects to internal names. This has not had an independent security review. If you expose this to the public, also restrict outbound traffic at the network level, which is the stronger control.
