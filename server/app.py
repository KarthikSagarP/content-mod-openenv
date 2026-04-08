"""
FastAPI application for the Content Moderation Environment.

Endpoints:
    - POST /reset: Reset the environment
    - POST /step: Execute a moderation action
    - GET /state: Get current environment state
    - GET /schema: Get action/observation schemas
    - WS /ws: WebSocket endpoint for persistent sessions
"""

from openenv.core.env_server.http_server import create_app

try:
    from ..models import ContentModAction, ContentModObservation
    from .content_mod_environment import ContentModEnvironment
except (ImportError, ModuleNotFoundError):
    from models import ContentModAction, ContentModObservation
    from server.content_mod_environment import ContentModEnvironment

app = create_app(
    ContentModEnvironment,
    ContentModAction,
    ContentModObservation,
    env_name="content_mod",
    max_concurrent_envs=4,
)


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
