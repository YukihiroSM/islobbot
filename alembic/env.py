import sys
from pathlib import Path

# Add the parent directory to sys.path to import modules from the main project
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import engine_from_config, pool
from alembic import context
from config import DATABASE_URL
from models import Base
from utils.logger import get_logger

logger = get_logger(__name__)

logger.info(f"Using database URL: {DATABASE_URL}")


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# add your model's MetaData object here
# for 'autogenerate' support

# Fetch the environment variable
database_url = DATABASE_URL

# Replace the sqlalchemy.url dynamically
config = context.config
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
    logger.debug("Set sqlalchemy.url in config")
else:
    logger.error("DATABASE_URL environment variable not set")
    raise RuntimeError("DATABASE_URL environment variable not set")

target_metadata = Base.metadata
# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    logger.info(f"Running migrations offline with URL: {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        logger.info("Starting offline migrations")
        context.run_migrations()
        logger.info("Completed offline migrations")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    logger.info("Running migrations online")
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        logger.debug("Connected to database")
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            logger.info("Starting online migrations")
            context.run_migrations()
            logger.info("Completed online migrations")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
