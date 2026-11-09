# Models and providers

**The report names no model or provider.** The system works fully with no model at all.

## What uses what

| Component | Method | Why |
|---|---|---|
| Grading | Tests in the sandbox, compared on the server | Must be exact and repeatable |
| Diagnostic facts | Runner output, tests, AST | Must be true, not plausible |
| Diagnostic inference, only when rules are unsure | Optional LLM | Rules cannot describe every misunderstanding |
| Mastery | Weighted Bayesian Knowledge Tracing | Explainable, works with little data |
| Confusion, load | Rules needing evidence | No labelled data exists to train on |
| Retrieval | Cosine search in ChromaDB, then rules | The report specifies it. No model needed. |
| DSDA | Rules from `policy.yaml` | Must be inspectable, and the LLM must not override it |
| Hint wording | Built-in templates, or optional LLM | An LLM can tailor wording to the learner's code |
| Hint validation | Rules | Safety must not depend on a model's judgement |
| Reflection wording | Templates, or optional LLM | Same as hints |
| Planner | Rules | Recommendations must be explainable |

**No model is trained here.** A large model would not be justified: no suitable labels exist, and it would be harder to explain. Deep Knowledge Tracing from the report's survey could replace BKT if real sequence data becomes available.

## Configuration

Set in `.env`. Keys stay on the server and never reach the browser.

| `LLM_PROVIDER` | Needs | Default model |
|---|---|---|
| `none` (default) | Nothing | Built-in hints |
| `openai` | `OPENAI_API_KEY` | `OPENAI_MODEL`, default `gpt-4o-mini` |
| `anthropic` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL`, default `claude-haiku-5-5` |
| `ollama` | A running local Ollama | `OLLAMA_MODEL`, default `qwen2.5-coder:1.5b` |

Any OpenAI-compatible server also works, by setting `OPENAI_BASE_URL`.

## Failure and fallback

| Situation | Behaviour |
|---|---|
| No provider, or no key | Built-in hints, with no warning needed |
| Provider error, quota, timeout (15 seconds) | Built-in hint, labelled "Standard hint", with a note that AI wording is unavailable |
| Malformed response | Same |
| Draft fails validation | Rewritten up to 3 attempts in total, then built-in |
| Level or strategy | Always from DSDA, whatever the model returns |

## Cost and latency

A submission that gets an AI hint makes 1 to 3 calls for the hint, plus possibly 1 for reflection and 1 when the diagnosis is uncertain. Each is capped: 260 output tokens for a hint (420 at L4), and less for the others. Without a provider, the agents add only a few milliseconds beyond the code run itself. Actual latency and token use are recorded on each stage in `agent_steps.llm`.

## Verification status

- **Adapters:** tested at the protocol level against mocked HTTP for OpenAI-compatible and Anthropic formats.
- **Pipeline behaviour:** tested with a scripted provider, including leaks, outages and prompt injection.
- **A real model has not been verified.** The OpenAI key in `backend/.env` returned `429 insufficient_quota` when tried. The hint quality of a real model, and the leak rate it would produce, are unknown until a key with credit is used.
