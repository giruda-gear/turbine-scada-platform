from uuid import UUID

from sqlalchemy.orm import Session

from scada_api.data_sources.schemas import DataSourceCreate
from scada_api.models import DataSource, Organization


def create_data_source(
    session: Session,
    data: DataSourceCreate,
) -> DataSource | None:
    organization = session.get(Organization, data.organization_id)

    if organization is None:
        return None

    data_source = DataSource(
        organization_id=data.organization_id,
        name=data.name,
        provider=data.provider,
        protocol=data.protocol,
        endpoint_url=data.endpoint_url,
    )

    session.add(data_source)
    session.commit()
    session.refresh(data_source)

    return data_source


def get_data_source(
    session: Session,
    data_source_id: UUID,
) -> DataSource | None:
    return session.get(DataSource, data_source_id)
