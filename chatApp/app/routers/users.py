from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter()


# =====================================================
# CREATE USER
# POST /users/
# =====================================================

@router.post("/", response_model=schemas.UserOut, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(models.User)
        .filter(models.User.email == user.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


# =====================================================
# LOGIN
# POST /users/login
# =====================================================

@router.post("/login", response_model=schemas.TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(models.User.email == form.username)
        .first()
    )

    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


# =====================================================
# GET USER BY ID
# GET /users/{user_id}
# =====================================================

@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(models.User, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


# =====================================================
# GET USER CONVERSATIONS
# GET /users/{user_id}/conversations
# =====================================================

@router.get(
    "/{user_id}/conversations",
    response_model=list[schemas.ConversationOut]
)
def get_user_conversations(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.get(models.User, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user.conversations
