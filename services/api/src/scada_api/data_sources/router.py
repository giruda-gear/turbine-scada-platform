from fastapi import APIRouter, HTTPException, status

from scada_api.data_sources import service
from scada_api.data_sources.schemas import DataSourceCreate, DataSourceResponse
from scada_api.dependencies import SessionDep

router = APIRouter(prefix="/data-sources", tags=["data-sources"])


@router.post(
    "",
    response_model=DataSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(data: DataSourceCreate, session: SessionDep):
    return service.create_data_source(session, data)


@router.get(
    "/{data_source_id}",
    response_model=DataSourceResponse,
)
def get_organization(data_source_id, session: SessionDep):
    organization = service.get_data_source(session, data_source_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization
