from __future__ import annotations

from redis import Redis
from rq import Worker

from ..config.settings import EnterpriseSettings
from ..storage.postgres.session import migrate_schema


def main() -> None:
    settings = EnterpriseSettings.from_env()
    migrate_schema()
    redis = Redis.from_url(settings.redis_url)
    worker = Worker(
        [settings.feedback_queue, settings.promotion_queue, settings.projection_queue],
        connection=redis,
    )
    worker.work()


if __name__ == "__main__":
    main()
