from fastapi import APIRouter, HTTPException, status
from app.schemas.auth import UserLogIn, UserSignUp
import logging

from app.services.auth import login_user, signup_user


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
async def login(user_in: UserLogIn):
    try:
        res = await login_user(user_in.email, user_in.password)

        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "token_type": "bearer",
            "user": res.user.model_dump() if res.user else None,
        }

    except Exception as e:
        logger.exception("Login failed")
        msg = getattr(e, "detail", None) or str(e) or e.__class__.__name__
        raise HTTPException(status_code=400, detail=msg)


@router.post("/sign-up", status_code=status.HTTP_201_CREATED)
async def sign_up(user_in: UserSignUp):
    try:
        user = await signup_user(user_in.email, user_in.password)
        return {"message": "User created", "user": user.model_dump() if user else None}
    except Exception as e:
        logger.exception("Sign-up failed")
        msg = getattr(e, "detail", None) or str(e) or e.__class__.__name__
        raise HTTPException(status_code=400, detail=msg)
