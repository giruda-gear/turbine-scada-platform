from fastapi import APIRouter

from scada_api.data_sources.router import router as data_source_router
from scada_api.organizations.router import router as organization_router
from scada_api.simulator.router import router as simulator_router
from scada_api.turbines.router import router as turbine_router

api_router = APIRouter()

api_router.include_router(router=data_source_router)
api_router.include_router(router=organization_router)
api_router.include_router(router=simulator_router)
api_router.include_router(router=turbine_router)
