import sqlite3
from fastapi import FastAPI, Form, Cookie, Response
from fastapi.responses import HTMLResponse
import uvicorn

db_name = "iaw301"


def init_db():
    connection = sqlite3.connect(database=db_name)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cursor.executemany("""
        INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)
    """, [
        ("admin", "123"),
        ("user1", "456"),
        ("user2", "password3")
    ])

    connection.commit()
    cursor.close()
    connection.close()


def get_connection():
    return sqlite3.connect(database=db_name)


init_db()

app = FastAPI(title="iaw301_webapp")


# ---------- /ping ----------
@app.get("/ping")
def ping():
    return "pong"


# ---------- /all ----------
@app.get("/all", response_class=HTMLResponse)
def get_all_users():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, username, password FROM users")
    rows = cursor.fetchall()
    cursor.close()
    connection.close()

    rows_html = "".join(
        f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td></tr>"
        for row in rows
    )

    return HTMLResponse(content=f"""
    <html>
        <head>
            <title>All Users</title>
        </head>
        <meta charset="UTF-8">
        <body>
            <h1>Users</h1>
            <table border="1" cellpadding="5" cellspacing="0">
                <tr>
                    <th>id</th>
                    <th>username</th>
                    <th>password</th>
                </tr>
                {rows_html}
            </table>
        </body>
    </html>
    """)


# ---------- / and /login-form ----------
@app.get("/", response_class=HTMLResponse)
@app.get("/login-form", response_class=HTMLResponse)
def get_login_form():
    return HTMLResponse(content="""
    <html>
        <head>
            <title>Login</title>
        </head>
        <meta charset="UTF-8">
        <body>
            <h1>Login</h1>
            <form action="/login" method="post">
                <label for="username">Username/Email:</label>
                <input type="text" id="username" name="username" required><br><br>
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required><br><br>
                <input type="submit" value="Login">
            </form>
        </body>
    </html>
    """)


# ---------- /login ----------
@app.post("/login", response_class=HTMLResponse)
def login(response: Response, username: str = Form(...), password: str = Form(...)):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if user:
        html = HTMLResponse(content=f"""
        <html>
            <head><title>Login</title></head>
            <meta charset="UTF-8">
            <body>
                <h1>Login thanh cong</h1>
                <p>Xin chao, {username}!</p>
                <a href="/logout">Logout</a>
            </body>
        </html>
        """)
        html.set_cookie(key="session_user", value=username, httponly=True)
        return html
    else:
        return HTMLResponse(content="""
        <html>
            <head><title>Login</title></head>
            <meta charset="UTF-8">
            <body>
                <h1>Login that bai</h1>
                <p>Sai username hoac password.</p>
                <a href="/login-form">Quay lai</a>
            </body>
        </html>
        """, status_code=401)


# ---------- /logout ----------
@app.get("/logout", response_class=HTMLResponse)
def logout(session_user: str = Cookie(default=None)):
    response = HTMLResponse(content="""
    <html>
        <head><title>Logout</title></head>
        <meta charset="UTF-8">
        <body>
            <h1>Da dang xuat</h1>
            <a href="/login-form">Dang nhap lai</a>
        </body>
    </html>
    """)
    response.delete_cookie(key="session_user")
    return response


if __name__ == "__main__":
    uvicorn.run(app=app, host="127.0.0.1", port=8888)