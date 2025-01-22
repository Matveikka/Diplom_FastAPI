from fastapi import APIRouter, Form, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from urllib.parse import quote
from fastapi import Cookie
import sqlite3
import re

router = APIRouter()
templates = Jinja2Templates(directory="templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db_connection():
    conn = sqlite3.connect('database.db')
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


def init_superuser():
    conn = get_db_connection()
    conn.execute(
        'CREATE TABLE IF NOT EXISTS users ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'username TEXT NOT NULL UNIQUE, '
        'password TEXT NOT NULL, '
        'is_superuser BOOLEAN NOT NULL DEFAULT 0)')
    if not conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone():
        password = '12345'
        hashed_password = pwd_context.hash(password)
        conn.execute('INSERT INTO users (username, password, is_superuser) VALUES (?, ?, ?)',
                     ('admin', hashed_password, 1))
    conn.commit()
    conn.close()


def set_cookie(response: HTMLResponse, username: str):
    response.set_cookie(key="username", value=username)


def get_current_user(username: str = Cookie(None)):
    if username:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return user
    return None


def is_superuser(user):
    return user and user['is_superuser'] == 1


@router.get('/home_page')
async def all_posts(request: Request, user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY created_at DESC').fetchall()
    conn.close()
    superuser_status = is_superuser(user)
    return templates.TemplateResponse('home.html',
                                      {"request": request, "posts": posts, "is_superuser": superuser_status})


@router.post('/home_page')
async def all_posts(request: Request, user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY created_at DESC').fetchall()
    conn.close()
    superuser_status = is_superuser(user)
    return templates.TemplateResponse('home.html',
                                      {"request": request, "posts": posts, "is_superuser": superuser_status})


@router.get('/posts/{slug}')
async def get_post(slug: str, request: Request, user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE slug = ?', (slug,)).fetchone()
    conn.close()
    superuser_status = is_superuser(user)
    return templates.TemplateResponse('details.html',
                                      {"request": request, "post": post, "is_superuser": superuser_status})


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
    return RedirectResponse(url='/home_page')


def generate_slug(title):
    slug = re.sub(r'[^a-zA-Zа-яА-Я0-9-]', '-', title.lower())
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


@router.post('/posts/{slug}/delete')
async def delete_post(slug: str):
    conn = get_db_connection()
    post = conn.execute('SELECT title, info, created_at FROM posts WHERE slug = ? ', (slug,)).fetchone()
    title = post['title']
    conn.execute('DELETE FROM posts WHERE slug = ?', (slug,))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f'/posts/deleted/{quote(title)}', status_code=303)


@router.get('/posts/deleted/{title}')
async def after_delete(title: str, request: Request):
    return templates.TemplateResponse('after_delete.html', {"request": request, "post": {"title": title}})


@router.get('/')
async def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post('/')
async def register(username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует.")
    else:
        hashed_password = pwd_context.hash(password)
        conn.execute('INSERT INTO users (username, password, is_superuser) VALUES (?, ?, ?)',
                     (username, hashed_password, 0))
        conn.commit()
    conn.close()
    return RedirectResponse(url='/login')


@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if user and pwd_context.verify(password, user['password']):
        response = RedirectResponse(url="/home_page")
        set_cookie(response, username)
        return response
    else:
        raise HTTPException(status_code=400, detail="Неверное имя пользователя или пароль!")
