import httpx
from fastapi import FastAPI, Query, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from image_search import image_to_query
from search_service import _env, render_results, search_all

MAX_IMAGE_BYTES = 10 * 1024 * 1024

app = FastAPI(title="Price Aggregator")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _env.get_template("index.html").render()


@app.get("/search", response_class=HTMLResponse)
async def search(q: str = Query(default="")):
    query = q.strip()
    if not query:
        return RedirectResponse(url="/", status_code=303)
    products = await search_all(query)
    return HTMLResponse(render_results(query, products))


@app.post("/resolve-image")
async def resolve_image(file: UploadFile):
    if not (file.content_type or "").startswith("image/"):
        return JSONResponse({"error": "Plik musi być obrazem."}, status_code=400)

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        return JSONResponse({"error": "Obraz jest za duży (max 10 MB)."}, status_code=413)

    try:
        query = await image_to_query(image_bytes)
    except RuntimeError as e:
        # Missing API key — configuration problem, not the user's fault.
        return JSONResponse({"error": str(e)}, status_code=503)
    except httpx.HTTPStatusError as e:
        print(f"[vision] HTTP {e.response.status_code}: {e.response.text[:300]}", flush=True)
        return JSONResponse(
            {"error": f"Vision API błąd {e.response.status_code}: {e.response.text[:200]}"},
            status_code=502,
        )
    except httpx.HTTPError as e:
        print(f"[vision] request error: {e}", flush=True)
        return JSONResponse(
            {"error": "Rozpoznawanie obrazu nie powiodło się. Spróbuj ponownie."},
            status_code=502,
        )

    return JSONResponse({"query": query})
