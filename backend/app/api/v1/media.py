from app.schemas.outputs import AssetOut
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from app.core.dependencies import DB, CurrentUser, CSRF
from app.core.config import settings
from app.middleware.rate_limit import rate
from app.services.media import create_upload, media_access
from app.services.presenters import asset_summary
from app.integrations.storage import storage, LocalStorage

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("", status_code=201, dependencies=[CSRF], response_model=AssetOut)
def upload(request: Request, db: DB, user: CurrentUser, file: UploadFile = File(...)):
    rate(request, "uploads", 15, user.id)
    data = file.file.read(settings.upload_max_mb * 1024 * 1024 + 1)
    if not data or len(data) > settings.upload_max_mb * 1024 * 1024:
        raise HTTPException(413, f"Choose a file under {settings.upload_max_mb} MB")
    return asset_summary(create_upload(db, user.id, data))


@router.get("/{media_id}")
def download(media_id: str, db: DB, user: CurrentUser):
    asset = media_access(db, media_id, user.id)
    store = storage()
    headers = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
    if isinstance(store, LocalStorage):
        return FileResponse(store.path(asset.object_key), media_type=asset.mime_type, headers=headers)
    return RedirectResponse(store.url(asset.object_key), headers=headers)
