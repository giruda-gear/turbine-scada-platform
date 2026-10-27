from uuid import UUID

from sqlalchemy.orm import Session

from scada_api.models.organization import Organization
from scada_api.organizations.schema import OrganizationCreate


def create_organization(session: Session, data: OrganizationCreate) -> Organization:
    organization = Organization(name=data.name)

    session.add(organization)
    session.commit()
    session.refresh(organization)

    return organization


def get_organazation(session: Session, organization_id: UUID) -> Organization | None:
    return session.get(Organization, organization_id)
