from fastapi import APIRouter, HTTPException

from scada_api.dependencies import SessionDep
from scada_api.organizations.schema import OrganizationResponse
from scada_api.organizations.service import get_organazation

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def get_organization(organization_id, session: SessionDep):
    organization = get_organazation(session, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )
    return organization
