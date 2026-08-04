import sqlite3

DB_NAME = "tienda.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Tabla de productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            image TEXT
        )
    ''')

    # Tabla de órdenes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT DEFAULT 'Pendiente',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insertar productos de ejemplo si la tabla está vacía
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("Camiseta Minimalista", "Camiseta 100% algodón de alta calidad", 25.00, 50, "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500"),
            ("Zapatillas Urbanas", "Zapatillas cómodas para el día a día", 60.00, 30, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500"),
            ("Mochila Exec", "Mochila resistente al agua con compartimento para laptop", 45.00, 20, "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500")
        ]
        cursor.executemany('INSERT INTO products (name, description, price, stock, image) VALUES (?, ?, ?, ?, ?)', sample_products)
        conn.commit()

    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn