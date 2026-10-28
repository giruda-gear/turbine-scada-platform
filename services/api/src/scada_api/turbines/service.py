from uuid import UUID

from sqlalchemy.orm import Session

from scada_api.models.organization import Organization
from scada_api.models.turbine import Turbine
from scada_api.turbines.schema import TurbineCreate


def create_turbine(session: Session, data: TurbineCreate) -> Turbine | None:
    organization = session.get(Organization, data.organization_id)

    if organization is None:
        return None

    turbine = Turbine(
        organization_id=data.organization_id,
        name=data.name,
    )

    session.add(turbine)
    session.commit()
    session.refresh(turbine)

    return turbine


def get_turbine(session: Session, turbine_id: UUID) -> Turbine | None:
    return session.get(Turbine, turbine_id)
