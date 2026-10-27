from uuid import UUID

from sqlalchemy.orm import Session

from scada_api.models.turbine import Turbine


def get_turbine(session: Session, turbine_id: UUID) -> Turbine | None:
    return session.get(Turbine, turbine_id)
