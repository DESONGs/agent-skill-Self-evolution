from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..config.settings import EnterpriseSettings
from ..jobs.queue import QueueManager
from ..storage.object_store.client import ObjectStoreClient
from ..storage.postgres.session import create_session_factory, create_sqlalchemy_engine
from ..storage.repositories.job_repository import JobRepository
from ..storage.repositories.lab_repository import LabRepository
from ..storage.repositories.registry_repository import RegistryRepository
from .execution_service import ExecutionService
from .feedback_service import FeedbackService
from .projection_service import ProjectionService
from .promotion_service import LabPromotionOrchestrator
from .registry_service import EnterpriseRegistryService


@dataclass(frozen=True)
class ServiceContainer:
    settings: EnterpriseSettings
    registry_service: EnterpriseRegistryService
    projection_service: ProjectionService
    execution_service: ExecutionService
    feedback_service: FeedbackService
    promotion_service: LabPromotionOrchestrator
    queue_manager: QueueManager
    job_repository: JobRepository
    object_store: ObjectStoreClient


@lru_cache(maxsize=1)
def get_service_container() -> ServiceContainer:
    settings = EnterpriseSettings.from_env()
    engine = create_sqlalchemy_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    object_store = ObjectStoreClient(settings)
    registry_repository = RegistryRepository(session_factory)
    lab_repository = LabRepository(session_factory)
    job_repository = JobRepository(session_factory)
    registry_service = EnterpriseRegistryService(registry_repository, object_store)
    queue_manager = QueueManager(settings, job_repository)
    projection_service = ProjectionService(registry_service)
    execution_service = ExecutionService(registry_repository, object_store)
    feedback_service = FeedbackService(registry_service, queue_manager)
    promotion_service = LabPromotionOrchestrator(
        lab_repository=lab_repository,
        registry_service=registry_service,
        object_store=object_store,
    )
    return ServiceContainer(
        settings=settings,
        registry_service=registry_service,
        projection_service=projection_service,
        execution_service=execution_service,
        feedback_service=feedback_service,
        promotion_service=promotion_service,
        queue_manager=queue_manager,
        job_repository=job_repository,
        object_store=object_store,
    )
