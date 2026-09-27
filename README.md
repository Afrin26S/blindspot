# BlindSpot

**Give a new developer — or a rushed reviewer — the map of a codebase AND the map of where it's dangerous, in one pass.**

Built for the IBM Bob 2.0 Hackathon, September 2026.

## 🔗 Live Demo

See the actual generated report from our demo run: **[blindspot-khaki.vercel.app](https://blindspot-khaki.vercel.app)**

This is the real output — architecture diagram, risk-ranked functions, and the verified doc-drift findings — not a mockup.

## The problem

Onboarding onto an unfamiliar codebase and finding its riskiest, least-tested
code are usually two separate manual efforts. BlindSpot does both in one run:
it maps the architecture for a new developer, and separately ranks every
function by real risk (complexity + how often it changes + whether it has
any test coverage) — then generates real tests for the riskiest ones and
checks whether the docs still match the code.

## What it does

1. **Architecture map** — analyzes the repo's structure and entry points,
   and (using Bob's Agent mode + a parallel `explore` subagent) writes a
   plain-English architecture overview with a Mermaid diagram of how the
   main modules relate.
2. **Risk-ranked functions + generated tests** — computes a risk score per
   function from cyclomatic complexity, git churn, and a test-coverage
   signal, then has Bob write real pytest tests for the riskiest ones.
3. **Verified doc-drift check** — compares the README and config against
   actual runtime behavior, but *verifies every candidate finding by
   actually running the code* before reporting it, instead of reporting
   anything that merely sounds plausible.

## Why the verification step matters

On our demo run against [miguelgrinberg/microblog](https://github.com/miguelgrinberg/microblog)
(the Flask Mega-Tutorial app), the drift-check step initially produced three
confident-sounding findings. Before finalizing them, we asked Bob to verify
each one by actually running the relevant code — and all three turned out to
be false (a dependency conflict that didn't actually reproduce, a Redis
connection assumption that didn't hold because the client library connects
lazily, and a logging claim that ignored Flask's own default log handler).
The final report says so, honestly, instead of shipping unverified claims.
That's the point of the tool: catching **real, reproducible** issues, not
generating plausible-looking noise.

## Real results from this run

- **137 functions analyzed across 34 files**
- **18 tests generated, 18 passing** — 5 initially failed, revealing two
  genuine bugs in the test approach (a cross-session SQLAlchemy identity
  conflict, and a mock patched at the wrong import location), both
  diagnosed and fixed
- **3 candidate doc-drift findings, all verified and correctly retracted**
  when they didn't reproduce
- Built and verified end-to-end using **3.68 of 40 available Bobcoins**

## How it's built

- `analyze.py` — deterministic analysis (radon complexity + git churn +
  test-reference heuristic). No AI involved; keeps Bobcoin usage low by
  doing all the countable, mechanical work in plain Python.
- `render_report.py` — deterministic HTML report renderer. Combines
  `analysis.json` with the markdown Bob writes into one self-contained
  dashboard.
- Bob IDE (Agent mode + a parallel `explore` subagent) supplies the parts
  that genuinely need understanding: the architecture write-up, the
  generated tests, and the verified drift analysis.

## How to run it

```bash
# 1. Set up
git clone <this-repo-url> blindspot
cd blindspot
pip install radon

# 2. Clone a target repo to analyze (any repo you have rights to use)
git clone https://github.com/miguelgrinberg/microblog.git sample-repo

# 3. Run the deterministic analysis (0 AI cost)
python analyze.py sample-repo

# 4. In Bob IDE, Agent mode, ask it to:
#    - write ARCHITECTURE.md (with a subagent exploring the codebase)
#    - write tests/ for the top risky functions from analysis.json
#    - write DOC_DRIFT.md, verifying each candidate before reporting it

# 5. Render the final report (0 AI cost)
python render_report.py

# Open reports/index.html in your browser
```

## Project structure

```
blindspot/
├── analyze.py                       # deterministic analyzer
├── render_report.py                 # deterministic report renderer
├── analysis.json                    # generated: risk data
├── ARCHITECTURE.md                  # generated: architecture + diagram
├── DOC_DRIFT.md                     # generated: verified drift findings
├── tests/test_blindspot_generated.py # generated: real passing tests
├── reports/index.html               # final combined dashboard
└── bob_sessions/                    # Bob IDE task screenshots
```
