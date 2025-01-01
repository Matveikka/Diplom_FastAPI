from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from slugify import slugify

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db_connection():
    conn = sqlite3.connect('posts.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            rezume TEXT NOT NULL,
            info TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            slug TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def generate_slug(title: str) -> str:
    return slugify(title)


@router.get('/')
async def index(request: Request):
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY created_at DESC').fetchall()
    conn.close()
    return templates.TemplateResponse('home.html', {"request": request, "posts": posts})


@router.get('/new')
async def new_post_form(request: Request):
    return templates.TemplateResponse('add_post.html', {"request": request})


@router.post('/new')
async def new_post(title: str = Form(...), rezume: str = Form(...), info: str = Form(...)):
    slug = generate_slug(title)
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO posts (title, rezume, info, slug) VALUES (?, ?, ?, ?)',
                     (title, rezume, info, slug))
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Slug already exists.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

    return RedirectResponse(url='/', status_code=303)


@router.get('/posts/{slug}')
async def get_post(slug: str, request: Request):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE slug = ?', (slug,)).fetchone()
    conn.close()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return templates.TemplateResponse('details.html', {"request": request, "post": post})


@router.post('/posts/{slug}/delete')
async def delete_post(slug: str, request: Request):
    conn = get_db_connection()
    try:
        post = conn.execute('DELETE FROM posts WHERE slug = ?', (slug,))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()
    return templates.TemplateResponse('after_delete.html', {"request": request, "post": post})
