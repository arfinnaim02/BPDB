from alembic import context
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import get_engine

config = context.config
target_metadata = Base.metadata

if context.is_offline_mode():
    secret = get_settings().database_url
    if not secret:
        raise RuntimeError("Set DATABASE_URL before generating migration SQL")
    context.configure(
        url=secret.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    context.configure(
        connection=config.attributes["connection"],
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
