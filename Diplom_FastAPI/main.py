from fastapi import FastAPI
from routers import post

app = FastAPI()
app.include_router(post.router)

if __name__ == "__main__":
    import uvicorn

    post.init_db()
    uvicorn.run(app, host="127.0.0.1", port=8000)
