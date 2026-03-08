import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_NAME = 'nutrition.db'

MOCK_PRODUCTS =     [
    ('apple',   52,  0.3,  0.2, 14.0),
    ('banana',  89,  1.1,  0.3, 23.0),
    ('chicken', 165, 31.0, 3.6,  0.0),
    ('rice',    130, 2.7,  0.3, 28.0),
    ('bread',   265, 9.0,  3.3, 49.0),
    ('cheese',  402, 25.0, 33.0, 1.3),
    ('egg',     155, 13.0, 11.0, 1.1),
    ('milk',     61, 3.2,  3.3,  4.8),
    ('orange',   47, 0.9,  0.3, 12.0),
    ('carrot',   41, 0.9,  0.2, 10.0),
    ('tomato',   18, 0.9,  0.2,  3.9),
    ('potato',   77, 2.0,  0.1, 17.0),
    ('beef',    250, 26.0, 15.0, 0.0),
    ('fish',    100, 20.0, 1.2,  0.0),
    ('pasta',   131, 5.0,  1.1, 25.0),
    ('chicken sandwich',   250.5, 15.2, 8.5, 28.3),
    ('donut',   420, 6.2, 22.5, 48.5),
    ('hot dog', 290, 10.5, 15.0, 27.0),
    ('cake',    38.0, 5.5, 22.0, 38.0),
    ("crushed potatoes",    105, 2.5, 4.1, 15.5),
    ("borsch",  65, 4.5, 2.8, 5.2),
    ("sushi",   150, 4.5, 4.0, 28.0),
    ("cutlet",  180, 15.0, 11.0, 10.0),
    ("syrniki",220, 14.0, 11.0, 18.0),
    ("semolina porridge",110, 3.5, 3.2, 17.0),
    ("oatmeal",   88, 3.0, 1.7, 15.0),
    ("avocado",  160, 2.0, 14.7, 1.8),
    ("greek salad", 95, 2.2, 8.5, 3.5),
    ("caesar salad chicken", 165, 12.0, 10.5, 5.5),
    ("caesar salad shrimp",   140, 11.0, 8.0, 5.0),
    ("pineapple", 50, 0.5, 0.1, 13.1),
    ("coffee",      2, 0.1, 0.1, 0.3)
]


@contextmanager
def _db():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _db() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                calories_per_100g REAL NOT NULL,
                protein_per_100g  REAL NOT NULL,
                fat_per_100g      REAL NOT NULL,
                carbs_per_100g    REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                product_id   INTEGER NOT NULL,
                product_name TEXT    NOT NULL,
                grams        REAL    NOT NULL,
                calories     REAL    NOT NULL,
                protein      REAL DEFAULT 0,
                fat          REAL DEFAULT 0,
                carbs        REAL DEFAULT 0,
                date         TEXT    NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user_norms (
                user_id      INTEGER PRIMARY KEY,
                protein_norm REAL DEFAULT 0,
                fat_norm     REAL DEFAULT 0,
                carbs_norm   REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.executemany('''
            INSERT OR IGNORE INTO products
                (name, calories_per_100g, protein_per_100g, fat_per_100g, carbs_per_100g)
            VALUES (?, ?, ?, ?, ?)
        ''', MOCK_PRODUCTS)

def get_product_by_name(name):
    with _db() as cur:
        cur.execute('SELECT * FROM products WHERE name = ?', (name.lower(),))
        return cur.fetchone()


def search_product(name):
    with _db() as cur:
        cur.execute('''
            SELECT id, name, calories_per_100g, protein_per_100g, fat_per_100g, carbs_per_100g
            FROM products WHERE name LIKE ?
        ''', (f'%{name.lower()}%',))
        return cur.fetchone()

def add_entry(user_id, product_id, product_name, grams, calories,
              protein=0, fat=0, carbs=0):
    date = datetime.now().strftime('%Y-%m-%d')
    print(f"   {product_id}{user_id}{product_name}: {grams}g = {calories} kcal {protein} {fat} {carbs}on {date}")
    with _db() as cur:
        cur.execute('''
            INSERT INTO entries
                (user_id, product_id, product_name, grams, calories, protein, fat, carbs, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, product_id, product_name, grams, calories, protein, fat, carbs, date))
        print("✅ DATABASE: Insert successful")

def get_daily_report(user_id, date=None):
    date = date or datetime.now().strftime('%Y-%m-%d')
    with _db() as cur:
        cur.execute('''
            SELECT product_name, grams, calories, protein, fat, carbs
            FROM entries WHERE user_id = ? AND date = ? ORDER BY created_at
        ''', (user_id, date))
        entries = cur.fetchall()
        cur.execute('''
            SELECT SUM(calories), SUM(protein), SUM(fat), SUM(carbs)
            FROM entries WHERE user_id = ? AND date = ?
        ''', (user_id, date))
        return entries, cur.fetchone()


def get_weekly_report(user_id):
    end = datetime.now()
    start = end - timedelta(days=7)
    s, e = start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
    with _db() as cur:
        cur.execute('''
            SELECT product_name, grams, calories, protein, fat, carbs, date
            FROM entries WHERE user_id = ? AND date >= ? AND date <= ?
            ORDER BY date, created_at
        ''', (user_id, s, e))
        entries = cur.fetchall()
        cur.execute('''
            SELECT SUM(calories), SUM(protein), SUM(fat), SUM(carbs)
            FROM entries WHERE user_id = ? AND date >= ? AND date <= ?
        ''', (user_id, s, e))
        return entries, cur.fetchone()


def set_user_norms(user_id, protein, fat, carbs):
    with _db() as cur:
        cur.execute('''
            INSERT OR REPLACE INTO user_norms
                (user_id, protein_norm, fat_norm, carbs_norm, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, protein, fat, carbs))


def get_user_norms(user_id):
    with _db() as cur:
        cur.execute(
            'SELECT protein_norm, fat_norm, carbs_norm FROM user_norms WHERE user_id = ?',
            (user_id,)
        )
        result = cur.fetchone()
    return result or (0, 0, 0)


if __name__ == '__main__':
    init_db()
    print(f"База данных '{DB_NAME}' инициализирована.")
    print(f"Загружено {len(MOCK_PRODUCTS)} mock-продуктов.")


