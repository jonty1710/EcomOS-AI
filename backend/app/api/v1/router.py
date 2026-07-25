from fastapi import APIRouter

from app.api.v1 import collection, knowledge, provenance, reports, research

api_router = APIRouter()
api_router.include_router(research.router)
api_router.include_router(reports.router)
api_router.include_router(collection.router)
api_router.include_router(knowledge.router)
api_router.include_router(provenance.router)
