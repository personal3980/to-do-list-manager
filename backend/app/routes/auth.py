"""Signup, cookie sessions, logout, and one-time password reset."""
import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..mail import send_reset_email
from ..models import AuthSession, PasswordReset, User, utcnow
from ..schemas import EmailInput, LoginInput, ResetInput, SignupInput, UserOutput
from ..security import DUMMY_HASH, limiter, password_hasher, token_hash

router = APIRouter(prefix='/api/auth', tags=['Authentication'])


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(config.COOKIE_NAME, '')
    session = db.get(AuthSession, token_hash(token)) if token else None
    if not session or session.expires_at <= utcnow():
        raise HTTPException(401, 'Please log in to continue.')
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, 'Please log in to continue.')
    return user


@router.post('/signup', response_model=UserOutput, status_code=201)
def signup(data: SignupInput, request: Request, db: Session = Depends(get_db)):
    limiter.check(request, 'signup', 10)
    user = User(name=data.name, email=str(data.email), password_hash=password_hasher.hash(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Unable to create an account with this email. Try logging in or resetting your password.')
    return user


@router.post('/login', response_model=UserOutput)
def login(data: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)):
    limiter.check(request, 'login', 20)
    # Serialize login with password reset so an old password cannot create a
    # fresh session after a concurrent reset has revoked existing sessions.
    user = db.scalar(select(User).where(User.email == str(data.email)).with_for_update())
    valid = password_hasher.verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, 'Email or password is incorrect.')
    old_token = request.cookies.get(config.COOKIE_NAME)
    if old_token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(old_token)))
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=token_hash(token), user_id=user.id,
                       expires_at=utcnow() + timedelta(seconds=config.SESSION_SECONDS)))
    db.commit()
    response.set_cookie(config.COOKIE_NAME, token, max_age=config.SESSION_SECONDS,
                        httponly=True, secure=config.COOKIE_SECURE, samesite='lax', path='/')
    return user


@router.get('/me', response_model=UserOutput)
def me(user: User = Depends(current_user)):
    return user


@router.post('/logout')
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(config.COOKIE_NAME)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie(config.COOKIE_NAME, path='/', secure=config.COOKIE_SECURE, httponly=True, samesite='lax')
    return {'message': 'You have been logged out.'}


@router.post('/forgot-password')
def forgot_password(data: EmailInput, request: Request, db: Session = Depends(get_db)):
    limiter.check(request, 'forgot-password', 5)
    user = db.scalar(select(User).where(User.email == str(data.email)))
    if user:
        token = secrets.token_urlsafe(32)
        # Multiple outstanding links may exist; successful reset revokes all of them.
        reset = PasswordReset(token_hash=token_hash(token), user_id=user.id,
                              expires_at=utcnow() + timedelta(seconds=config.RESET_SECONDS))
        db.execute(delete(PasswordReset).where(PasswordReset.expires_at <= utcnow()))
        db.add(reset)
        db.commit()
        try:
            send_reset_email(user.email, token)
        except Exception:
            # Do not log tokens, email contents, SMTP errors, or database credentials.
            logging.getLogger(__name__).error('Password reset email could not be delivered. Check mail configuration.')
            db.execute(delete(PasswordReset).where(PasswordReset.token_hash == reset.token_hash))
            db.commit()
    return {'message': 'If an account exists for that email, a password reset link has been sent.'}


@router.post('/reset-password')
def reset_password(data: ResetInput, request: Request, response: Response, db: Session = Depends(get_db)):
    limiter.check(request, 'reset-password', 10)
    # Lock the user first, then reread the token. Concurrent requests for the same
    # user serialize so only one reset can succeed, even with different links.
    record = db.get(PasswordReset, token_hash(data.token))
    if not record or record.expires_at <= utcnow():
        raise HTTPException(400, 'This reset link is invalid or expired. Request a new one.')
    user = db.scalar(select(User).where(User.id == record.user_id).with_for_update())
    record = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == token_hash(data.token))
                       .with_for_update().execution_options(populate_existing=True))
    if not user or not record or record.expires_at <= utcnow():
        raise HTTPException(400, 'This reset link is invalid or expired. Request a new one.')
    user.password_hash = password_hasher.hash(data.password)
    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.commit()
    response.delete_cookie(config.COOKIE_NAME, path='/', secure=config.COOKIE_SECURE, httponly=True, samesite='lax')
    return {'message': 'Password updated. Please log in with your new password.'}
