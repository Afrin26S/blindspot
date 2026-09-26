# Prevent the langsmith pytest plugin from loading — it has a broken
# pydantic/typing_extensions dependency in this environment.
collect_ignore_glob = []


def pytest_configure(config):
    # Deregister the langsmith plugin if it was registered via entry-points
    # before we could block it with -p no:langsmith.
    try:
        config.pluginmanager.set_blocked("langsmith")
    except Exception:
        pass
