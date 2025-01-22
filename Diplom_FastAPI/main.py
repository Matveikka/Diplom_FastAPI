from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import post

app = FastAPI()
app.include_router(post.router)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    post.init_db()
    post.init_superuser()
    uvicorn.run(app, host="127.0.0.1", port=8000)
