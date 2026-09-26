"""
Auto-generated pytest tests for the top-5 highest-risk functions identified by
the Blindspot analyser.

Covered:
  1. app/api/users.py  :: update_user     (risk 0.70)
  2. config.py         :: Config           (risk 0.67)
  3. app/models.py     :: after_commit     (risk 0.60)
  4. app/__init__.py   :: create_app       (risk 0.60)
  5. app/auth/routes.py:: login            (risk 0.60)
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Make sure sample-repo is on the path so we can import the app package.
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sample-repo'))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ---------------------------------------------------------------------------
# Shared app / test-client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def app():
    """Create an application instance configured for testing."""
    # Patch heavy optional dependencies that are not present in a plain
    # test environment (Elasticsearch, Redis/RQ).
    es_patch = patch('elasticsearch.Elasticsearch', MagicMock())
    redis_patch = patch('redis.Redis.from_url', MagicMock())
    rq_patch = patch('rq.Queue', MagicMock())

    es_patch.start()
    redis_patch.start()
    rq_patch.start()

    from app import create_app

    class TestConfig:
        TESTING = True
        SECRET_KEY = 'test-secret-key'
        SQLALCHEMY_DATABASE_URI = 'sqlite://'  # in-memory
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SERVER_NAME = 'localhost'
        WTF_CSRF_ENABLED = False
        MAIL_SERVER = None
        ELASTICSEARCH_URL = None
        REDIS_URL = 'redis://'
        LANGUAGES = ['en']
        MS_TRANSLATOR_KEY = None
        POSTS_PER_PAGE = 25
        LOG_TO_STDOUT = True

    flask_app = create_app(TestConfig)

    with flask_app.app_context():
        from app import db
        db.create_all()
        yield flask_app
        db.drop_all()

    es_patch.stop()
    redis_patch.stop()
    rq_patch.stop()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    from app import db as _db
    with app.app_context():
        yield _db
        _db.session.rollback()


# ---------------------------------------------------------------------------
# Helper: create a user in the DB
# ---------------------------------------------------------------------------

def make_user(db_session, username='alice', email='alice@example.com',
              password='secret'):
    from app.models import User
    import sqlalchemy as sa
    # Avoid duplicates across parametrised tests
    existing = db_session.session.scalar(
        sa.select(User).where(User.username == username))
    if existing:
        return existing
    u = User(username=username, email=email)
    u.set_password(password)
    db_session.session.add(u)
    db_session.session.commit()
    return u


# ===========================================================================
# 1. update_user  (app/api/users.py, line 66)
# ===========================================================================

class TestUpdateUser:
    """Tests for PUT /api/users/<id>."""

    def _auth_header(self, app, user):
        with app.app_context():
            from app import db
            # Merge the user into the current scoped session so get_token()
            # doesn't hit an "already attached to session X (this is Y)" error.
            merged = db.session.merge(user)
            token = merged.get_token()
            db.session.commit()
        return {'Authorization': f'Bearer {token}'}

    def test_update_about_me_happy_path(self, app, client, db_session):
        """Owner can update their own about_me field."""
        user = make_user(db_session, 'bob_upd', 'bob_upd@example.com')
        headers = self._auth_header(app, user)

        rv = client.put(
            f'/api/users/{user.id}',
            json={'about_me': 'Hello world'},
            headers=headers,
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['about_me'] == 'Hello world'

    def test_update_user_forbidden_for_other_user(self, app, client, db_session):
        """A user cannot update another user's profile — expect 403."""
        owner = make_user(db_session, 'carol_upd', 'carol_upd@example.com')
        other = make_user(db_session, 'dave_upd', 'dave_upd@example.com')
        headers = self._auth_header(app, other)

        rv = client.put(
            f'/api/users/{owner.id}',
            json={'about_me': 'Sneaky edit'},
            headers=headers,
        )
        assert rv.status_code == 403

    def test_update_user_duplicate_username_rejected(self, app, client, db_session):
        """Changing username to one already taken returns 400."""
        u1 = make_user(db_session, 'eve_upd', 'eve_upd@example.com')
        u2 = make_user(db_session, 'frank_upd', 'frank_upd@example.com')
        headers = self._auth_header(app, u1)

        rv = client.put(
            f'/api/users/{u1.id}',
            json={'username': u2.username},
            headers=headers,
        )
        assert rv.status_code == 400
        assert b'username' in rv.data


# ===========================================================================
# 2. Config  (config.py, line 8)
# ===========================================================================

class TestConfig:
    """Tests for the Config class in config.py."""

    def test_default_secret_key(self, monkeypatch):
        """SECRET_KEY falls back to hardcoded default when env var absent."""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        # Re-import with a clean env — we need to re-evaluate class body.
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        assert cfg_module.Config.SECRET_KEY == 'you-will-never-guess'

    def test_secret_key_from_env(self, monkeypatch):
        """SECRET_KEY is read from environment variable when set."""
        monkeypatch.setenv('SECRET_KEY', 'my-super-secret')
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        assert cfg_module.Config.SECRET_KEY == 'my-super-secret'

    def test_sqlite_fallback_when_no_database_url(self, monkeypatch):
        """SQLALCHEMY_DATABASE_URI falls back to sqlite when DATABASE_URL unset."""
        monkeypatch.delenv('DATABASE_URL', raising=False)
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        assert 'sqlite' in cfg_module.Config.SQLALCHEMY_DATABASE_URI

    def test_postgres_url_rewrite(self, monkeypatch):
        """postgres:// scheme is rewritten to postgresql:// for SQLAlchemy 1.4+."""
        monkeypatch.setenv('DATABASE_URL', 'postgres://user:pw@host/db')
        import importlib
        import config as cfg_module
        importlib.reload(cfg_module)
        assert cfg_module.Config.SQLALCHEMY_DATABASE_URI.startswith('postgresql://')


# ===========================================================================
# 3. SearchableMixin.after_commit  (app/models.py, line 41)
# ===========================================================================

class TestAfterCommit:
    """Tests for SearchableMixin.after_commit class method."""

    def _make_session_with_changes(self, adds=(), updates=(), deletes=()):
        session = MagicMock()
        session._changes = {
            'add': list(adds),
            'update': list(updates),
            'delete': list(deletes),
        }
        return session

    def test_add_triggers_add_to_index(self, app):
        """Objects added in a commit are indexed."""
        with app.app_context():
            from app.models import SearchableMixin
            import app.models as models_module

            # Use a real subclass so isinstance(obj, SearchableMixin) is True.
            class FakeSearchable(SearchableMixin):
                __tablename__ = 'post'

            obj = FakeSearchable()
            session = self._make_session_with_changes(adds=[obj])

            # Patch the names as they exist in app.models (where they are called),
            # not in app.search (where they are defined).
            with patch.object(models_module, 'add_to_index') as mock_add, \
                 patch.object(models_module, 'remove_from_index') as mock_rm:
                SearchableMixin.after_commit(session)
                mock_add.assert_called_once_with('post', obj)
                mock_rm.assert_not_called()

    def test_delete_triggers_remove_from_index(self, app):
        """Objects deleted in a commit are removed from the index."""
        with app.app_context():
            from app.models import SearchableMixin
            import app.models as models_module

            class FakeSearchable(SearchableMixin):
                __tablename__ = 'post'

            obj = FakeSearchable()
            session = self._make_session_with_changes(deletes=[obj])

            with patch.object(models_module, 'add_to_index') as mock_add, \
                 patch.object(models_module, 'remove_from_index') as mock_rm:
                SearchableMixin.after_commit(session)
                mock_rm.assert_called_once_with('post', obj)
                mock_add.assert_not_called()

    def test_non_searchable_objects_are_skipped(self, app):
        """Plain db.Model objects (not SearchableMixin) are ignored."""
        with app.app_context():
            from app.models import SearchableMixin
            from app import search as search_module

            # A plain object that does NOT inherit SearchableMixin
            plain_obj = MagicMock()
            # Ensure isinstance(plain_obj, SearchableMixin) is False
            plain_obj.__class__ = object

            session = self._make_session_with_changes(adds=[plain_obj])

            with patch.object(search_module, 'add_to_index') as mock_add:
                SearchableMixin.after_commit(session)
                mock_add.assert_not_called()

            assert session._changes is None  # always cleared


# ===========================================================================
# 4. create_app  (app/__init__.py, line 31)
# ===========================================================================

class TestCreateApp:
    """Tests for the app factory function."""

    def test_returns_flask_app(self, app):
        """create_app returns a Flask application instance."""
        from flask import Flask
        assert isinstance(app, Flask)

    def test_testing_flag_set(self, app):
        """TESTING config key is honoured."""
        assert app.config['TESTING'] is True

    def test_blueprints_registered(self, app):
        """All expected blueprints are registered."""
        bp_names = set(app.blueprints.keys())
        assert 'auth' in bp_names
        assert 'main' in bp_names
        assert 'api' in bp_names
        assert 'errors' in bp_names

    def test_api_url_prefix(self, app):
        """The api blueprint is mounted under /api."""
        with app.test_request_context():
            from flask import url_for
            url = url_for('api.get_users')
        assert url.startswith('/api/')

    def test_create_app_different_config(self):
        """create_app can be called with a second config without sharing state."""
        with patch('elasticsearch.Elasticsearch', MagicMock()), \
             patch('redis.Redis.from_url', MagicMock()), \
             patch('rq.Queue', MagicMock()):
            from app import create_app

            class AltConfig:
                TESTING = True
                SECRET_KEY = 'alt-key'
                SQLALCHEMY_DATABASE_URI = 'sqlite://'
                SQLALCHEMY_TRACK_MODIFICATIONS = False
                SERVER_NAME = 'alt.localhost'
                WTF_CSRF_ENABLED = False
                MAIL_SERVER = None
                ELASTICSEARCH_URL = None
                REDIS_URL = 'redis://'
                LANGUAGES = ['en']
                MS_TRANSLATOR_KEY = None
                POSTS_PER_PAGE = 10
                LOG_TO_STDOUT = True

            alt_app = create_app(AltConfig)
            assert alt_app.config['POSTS_PER_PAGE'] == 10


# ===========================================================================
# 5. login  (app/auth/routes.py, line 15)
# ===========================================================================

class TestLogin:
    """Tests for the /auth/login browser endpoint."""

    def test_login_happy_path_redirects_to_index(self, app, client, db_session):
        """Valid credentials redirect to the main index."""
        make_user(db_session, 'grace_login', 'grace@example.com', 'pw1234')

        rv = client.post(
            '/auth/login',
            data={'username': 'grace_login', 'password': 'pw1234',
                  'remember_me': False},
            follow_redirects=True,
        )
        assert rv.status_code == 200
        # After login the user lands on the index page (not re-shown the login form)
        assert b'Sign In' not in rv.data or b'grace_login' in rv.data

    def test_login_wrong_password_stays_on_login(self, app, client, db_session):
        """Wrong password flashes an error and stays on the login page."""
        make_user(db_session, 'heidi_login', 'heidi@example.com', 'correct')

        rv = client.post(
            '/auth/login',
            data={'username': 'heidi_login', 'password': 'wrong',
                  'remember_me': False},
            follow_redirects=True,
        )
        assert rv.status_code == 200
        assert b'Invalid username or password' in rv.data

    def test_login_nonexistent_user_flashes_error(self, app, client):
        """Unknown username also shows the invalid-credentials flash."""
        rv = client.post(
            '/auth/login',
            data={'username': 'nobody', 'password': 'irrelevant',
                  'remember_me': False},
            follow_redirects=True,
        )
        assert rv.status_code == 200
        assert b'Invalid username or password' in rv.data
