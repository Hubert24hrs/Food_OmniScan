from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select

from app.core.deps import DB, CurrentUser
from app.models import Product, ShoppingList, ShoppingListItem
from app.services import entitlements as ent
from app.services import households as hh

router = APIRouter(prefix="/shopping-lists", tags=["shopping"])


def list_out(sl: ShoppingList) -> dict:
    return {
        "id": sl.id,
        "name": sl.name,
        "shared_with_family": sl.shared_with_family,
        "household_id": sl.household_id,
        "items": [
            {"id": i.id, "text": i.text, "quantity": i.quantity, "checked": i.checked, "product_id": i.product_id}
            for i in sl.items
        ],
        "updated_at": sl.updated_at.isoformat(),
    }


def _owned(db, user, list_id) -> ShoppingList:
    sl = db.get(ShoppingList, list_id)
    if not sl or not hh.can_access(db, user, sl.owner_user_id, sl.household_id):
        raise HTTPException(404, "List not found")
    return sl


class ListIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    shared_with_family: bool = False


@router.get("")
def all_lists(db: DB, user: CurrentUser):
    hid = hh.household_id(db, user)
    cond = ShoppingList.owner_user_id == user.id
    if hid:
        cond = or_(cond, ShoppingList.household_id == hid)
    return [
        list_out(sl)
        for sl in db.scalars(select(ShoppingList).where(cond).order_by(ShoppingList.updated_at.desc())).all()
    ]


@router.post("", status_code=201)
def create(body: ListIn, db: DB, user: CurrentUser):
    count = len(db.scalars(select(ShoppingList.id).where(ShoppingList.owner_user_id == user.id)).all())
    ent.count_cap(db, user, "shopping_lists", count)
    hid = hh.household_id(db, user) if body.shared_with_family else None
    sl = ShoppingList(owner_user_id=user.id, name=body.name, shared_with_family=bool(hid), household_id=hid)
    db.add(sl)
    db.commit()
    return list_out(sl)


@router.delete("/{list_id}", status_code=204)
def delete(list_id: str, db: DB, user: CurrentUser):
    sl = _owned(db, user, list_id)
    if sl.owner_user_id != user.id:
        raise HTTPException(403, "Only the person who made this list can delete it")
    db.delete(sl)
    db.commit()


def add_lines(db, sl: ShoppingList, user, lines: list[dict]) -> int:
    """Add recipe or plan ingredients, skipping ones already on the list (case-insensitive)."""
    have = {i.text.strip().lower() for i in sl.items}
    n = 0
    for line in lines:
        text = line["text"].strip()[:200]
        if not text or text.lower() in have:
            continue
        sl.items.append(
            ShoppingListItem(list_id=sl.id, text=text, quantity=(line.get("quantity") or None), added_by=user.id)
        )
        have.add(text.lower())
        n += 1
    return n


def target_list(db, user, list_id: str | None, name: str) -> ShoppingList:
    if list_id:
        return _owned(db, user, list_id)
    count = len(db.scalars(select(ShoppingList.id).where(ShoppingList.owner_user_id == user.id)).all())
    ent.count_cap(db, user, "shopping_lists", count)
    sl = ShoppingList(owner_user_id=user.id, name=name[:120])
    db.add(sl)
    db.flush()
    return sl


class ItemIn(BaseModel):
    text: str | None = Field(default=None, max_length=200)
    product_id: str | None = None
    quantity: str | None = Field(default=None, max_length=40)


@router.post("/{list_id}/items", status_code=201)
def add_item(list_id: str, body: ItemIn, db: DB, user: CurrentUser):
    sl = _owned(db, user, list_id)
    text = body.text
    if body.product_id:
        p = db.get(Product, body.product_id)
        if not p:
            raise HTTPException(404, "Product not found")
        text = text or " ".join(filter(None, [p.brand_text, p.name])) or "Product"
    if not text:
        raise HTTPException(422, "Provide text or product_id")
    sl.items.append(
        ShoppingListItem(list_id=sl.id, text=text, product_id=body.product_id, quantity=body.quantity, added_by=user.id)
    )
    db.commit()
    return list_out(sl)


class ItemPatch(BaseModel):
    checked: bool | None = None
    quantity: str | None = Field(default=None, max_length=40)
    text: str | None = Field(default=None, max_length=200)


@router.patch("/{list_id}/items/{item_id}")
def patch_item(list_id: str, item_id: str, body: ItemPatch, db: DB, user: CurrentUser):
    sl = _owned(db, user, list_id)
    item = next((i for i in sl.items if i.id == item_id), None)
    if not item:
        raise HTTPException(404, "Item not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    return list_out(sl)


@router.delete("/{list_id}/items/{item_id}")
def delete_item(list_id: str, item_id: str, db: DB, user: CurrentUser):
    sl = _owned(db, user, list_id)
    item = next((i for i in sl.items if i.id == item_id), None)
    if not item:
        raise HTTPException(404, "Item not found")
    sl.items.remove(item)
    db.commit()
    return list_out(sl)
