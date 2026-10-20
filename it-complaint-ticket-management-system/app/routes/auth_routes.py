
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_account,
)
from app.database import get_db
from app.models import AuthAccount, User, Staff

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ---------------- USER REGISTRATION ----------------

class RegisterRequest(BaseModel):
    user_id: int = Field(gt=0)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.user_id == data.user_id
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    email = str(data.email).lower()

    if user.email.lower() != email:
        raise HTTPException(
            status_code=400,
            detail="Email does not match the selected user"
        )

    existing = db.query(AuthAccount).filter(
        AuthAccount.email == email
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account already exists for this email"
        )

    account = AuthAccount(
        email=email,
        password_hash=hash_password(data.password),
        role="User",
        user_id=user.user_id
    )

    try:
        db.add(account)
        db.commit()
        db.refresh(account)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account already exists for this user or email"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create account"
        )

    return {
        "message": "Registration successful",
        "email": account.email,
        "role": account.role
    }


# ---------------- LOGIN ----------------

@router.post("/login")
def login(
    
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    
    email = form.username.strip().lower()

    account = db.query(AuthAccount).filter(
        AuthAccount.email == email
    ).first()

    if not account or not verify_password(
        form.password,
        account.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token({
        "sub": str(account.account_id),
        "role": account.role,
        "email": account.email
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": account.role
    }


# ---------------- CURRENT ACCOUNT ----------------

@router.get("/me")
def get_my_account(
    current_account: AuthAccount = Depends(get_current_account),
    db: Session = Depends(get_db)
):
    result = {
        "account_id": current_account.account_id,
        "email": current_account.email,
        "role": current_account.role,
        "is_team_lead": False,
        "user": None,
        "staff": None
    }

    if current_account.user_id:
        user = db.query(User).filter(
            User.user_id == current_account.user_id
        ).first()

        if user:
            result["user"] = {
                "user_id": user.user_id,
                "name": getattr(user, "name", None),
                "email": getattr(user, "email", current_account.email)
            }

    if current_account.staff_id:
        staff = db.query(Staff).filter(
            Staff.staff_id == current_account.staff_id
        ).first()

        if staff:
            is_lead = bool(getattr(staff, "is_team_lead", False))
            result["is_team_lead"] = is_lead
            result["staff"] = {
                "staff_id": staff.staff_id,
                "name": getattr(staff, "name", None),
                "email": getattr(staff, "email", current_account.email),
                "is_team_lead": is_lead
            }

    return result


# ---------------- STAFF ACCOUNT CREATION ----------------

class StaffAccountCreate(BaseModel):
    staff_id: int = Field(gt=0)
    password: str = Field(min_length=8, max_length=72)


@router.post(
    "/staff-register",
    status_code=status.HTTP_201_CREATED
)
def create_staff_account(
    data: StaffAccountCreate,
    db: Session = Depends(get_db),
    current_account: AuthAccount = Depends(get_current_account)
):
    is_admin = current_account.role == "Admin"
    is_team_lead = False

    if current_account.role == "Staff" and current_account.staff_id:
        current_staff = db.query(Staff).filter(
            Staff.staff_id == current_account.staff_id
        ).first()

        if current_staff:
            is_team_lead = bool(
                getattr(current_staff, "is_team_lead", False)
            )

    if not is_admin and not is_team_lead:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Team Leads or Admins can create staff accounts"
        )

    staff = db.query(Staff).filter(
        Staff.staff_id == data.staff_id
    ).first()

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Staff record not found"
        )

    existing = db.query(AuthAccount).filter(
        (AuthAccount.staff_id == staff.staff_id)
        | (AuthAccount.email == staff.email)
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account already exists for this staff member or email"
        )

    account = AuthAccount(
        email=staff.email,
        password_hash=hash_password(data.password),
        role="Staff",
        staff_id=staff.staff_id
    )

    try:
        db.add(account)
        db.commit()
        db.refresh(account)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account already exists for this staff member or email"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create staff account"
        )

    return {
        "message": "Staff account created successfully",
        "staff_id": staff.staff_id,
        "email": account.email,
        "role": account.role
    }
