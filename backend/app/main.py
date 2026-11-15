"""Run from backend: python -m uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from . import config
from .database import Base, engine
from .routes.auth import router


@asynccontextmanager
async def lifespan(app):
    # Creates missing tables only; does not alter or delete existing tables.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title='Taskwell Authentication API', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[config.FRONTEND_ORIGIN],
                   allow_credentials=True, allow_methods=['GET', 'POST'],
                   allow_headers=['Content-Type'])


@app.middleware('http')
async def protect_requests(request: Request, call_next):
    if request.method == 'POST':
        # Allow the configured frontend and same-origin API docs. Native API
        # clients may omit Origin; JSON-only input and restricted CORS prevent
        # an untrusted browser page from using that path for a form submission.
        origin = request.headers.get('origin')
        api_origin = f'{request.url.scheme}://{request.url.netloc}'
        if ((origin is not None and origin not in {config.FRONTEND_ORIGIN, api_origin})
                or (origin is None and request.headers.get('sec-fetch-site') == 'cross-site')):
            return JSONResponse({'detail': 'Untrusted request origin.'}, status_code=403)
        if request.headers.get('content-type', '').split(';')[0].strip() != 'application/json':
            return JSONResponse({'detail': 'Send an application/json request.'}, status_code=415)
        # Bound JSON input before validation/password hashing.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 8192:
                return JSONResponse({'detail': 'Request is too large.'}, status_code=413)
        request._body = bytes(body)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Default validation errors can echo passwords/tokens in their input fields.
    errors = [{'field': '.'.join(str(x) for x in error['loc'][1:]), 'message': error['msg']}
              for error in exc.errors()]
    return JSONResponse({'detail': 'Please check the submitted fields.', 'errors': errors}, status_code=422)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse({'detail': 'Database unavailable. Please try again later.'}, status_code=503)


app.include_router(router)
