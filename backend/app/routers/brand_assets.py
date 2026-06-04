from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from app.core.deps import get_current_user, require_editor
from app.models.user import User
from app.models.brand_asset import BrandAsset, BrandAssetCreate, BrandAssetUpdate, BrandAssetRead

router = APIRouter()


@router.get("", response_model=list[BrandAssetRead])
def list_assets(
    categoria: Optional[str] = None,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(BrandAsset)
    if categoria:
        q = q.where(BrandAsset.categoria == categoria)
    q = q.order_by(BrandAsset.categoria, BrandAsset.id)
    return session.exec(q).all()


@router.post("", response_model=BrandAssetRead)
def create_asset(
    data: BrandAssetCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    asset = BrandAsset(**data.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@router.put("/{asset_id}", response_model=BrandAssetRead)
def update_asset(
    asset_id: int,
    data: BrandAssetUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    asset = session.get(BrandAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(asset, k, v)
    asset.updated_at = datetime.utcnow()
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_editor),
):
    asset = session.get(BrandAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    session.delete(asset)
    session.commit()
    return {"ok": True}
