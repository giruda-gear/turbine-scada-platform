from fastapi import APIRouter, HTTPException, status  # noqa: I001


from scada_api.dependencies import SessionDep
from scada_api.organizations.schema import OrganizationCreate, OrganizationResponse
from scada_api.organizations import service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(data: OrganizationCreate, session: SessionDep):
    return service.create_organization(session, data)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
)
def get_organization(organization_id, session: SessionDep):
    organization = service.get_organazation(session, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization
