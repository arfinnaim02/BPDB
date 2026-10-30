from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    secret = get_settings().database_url
    if secret is None:
        raise RuntimeError("DATABASE_URL is not configured")
    return create_engine(
        secret.get_secret_value(),
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": 10},
        hide_parameters=True,
    )


def session_factory() -> sessionmaker[Session]:
    return sessionmaker(get_engine(), expire_on_commit=False)
