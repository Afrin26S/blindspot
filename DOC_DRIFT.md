# Doc Drift Report

Files checked against code: `app/__init__.py`, `app/auth/routes.py`,
`app/main/routes.py`, `app/api/users.py`, `requirements.txt`, `tests.py`,
`.flaskenv`.

---

## No reproducible contradictions found

Each candidate finding was verified by running the code before being included.
All three candidates were invalidated:

| Candidate | Claim | Actual behaviour |
|---|---|---|
| `requirements.txt` Flask-Mail 0.9.1 + Flask 3.0 | `from flask_mail import Mail` would raise `ImportError` | Import succeeds — Flask-Mail 0.9.1 works under Flask 3.0 in this environment |
| `tests.py` missing Redis stub | `create_app()` raises `ConnectionError` without Redis | `redis.Redis.from_url()` and `rq.Queue()` are lazy; they construct without a live server and only fail on the first actual command |
| `.flaskenv` `FLASK_DEBUG=1` | Logger has no handlers, all output silently dropped | Flask's own debug mode attaches a `StreamHandler` to stderr; `app.logger` is never silent |

The README contains no technical claims to contradict. The deployment files
(`Dockerfile`, `boot.sh`, `Procfile`) are consistent with what `microblog.py`
and `app/__init__.py` actually do.
