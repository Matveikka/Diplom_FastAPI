from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import re

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db_connection():
    conn = sqlite3.connect('posts.db')
    conn.row_factory = sqlite3.Row
    return conn


def close_db_connection(conn):
    conn.close()


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


def generate_slug(title):
    slug = re.sub(r'[^a-zA-Z0-9-]', '-', title.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    conn = get_db_connection()
    cursor = conn.cursor()
    original_slug = slug
    count = cursor.execute('SELECT COUNT(*) FROM posts WHERE slug = ?', (slug,)).fetchone()[0]
    i = 1
    while count > 0:
        slug = f"{original_slug}-{i}"
        count = cursor.execute('SELECT COUNT(*) FROM posts WHERE slug = ?', (slug,)).fetchone()[0]
        i += 1
    close_db_connection(conn)
    return slug


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
    conn.execute('INSERT INTO posts (title, rezume, info, slug) VALUES (?, ?, ?, ?)',
                 (title, rezume, info, slug))
    conn.commit()
    conn.close()
    return RedirectResponse(url='/', status_code=303)


@router.get('/posts/{slug}')
async def get_post(slug: str, request: Request):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE slug = ?', (slug,)).fetchone()
    conn.close()
    return templates.TemplateResponse('details.html', {"request": request, "post": post})


@router.post('/posts/{slug}/delete')
async def delete_post(slug: str, request: Request):
    conn = get_db_connection()
    post = conn.execute('DELETE FROM posts WHERE slug = ?', (slug,))
    conn.commit()
    conn.close()
    return templates.TemplateResponse('after_delete.html', {"request": request, "post": post})
