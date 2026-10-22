from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/favicon.ico", include_in_schema=False)
async def disable_favicon() -> Response:
    return Response(status_code=204)


@router.get("/", response_class=FileResponse)
async def hello(request: Request) -> FileResponse:
    static_dir = request.app.state.static_dir
    return FileResponse(f"{static_dir}/index.html")
