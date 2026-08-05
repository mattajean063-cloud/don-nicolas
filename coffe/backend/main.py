from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Any

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# ==========================================
# CONFIGURACIÓN DE CORREO ELECTRÓNICO
# ==========================================
def enviar_alerta_correo(pedido_id: int, cliente: str, total: float, telefono: str, direccion: str):
    # Correo del negocio que recibirá la alerta y correo emisor
    remitente = "mattajean063@gmail.com"
    password = "matamata6754" # Contraseña de aplicación de Gmail
    destinatario = "mattajean063@gmail.com" # Puede ser el mismo o el del administrador
    
    asunto = f"¡Nuevo Pedido Recibido! #{pedido_id}"
    cuerpo = f"""
    ¡Hola! Hay un nuevo pedido en Don Nicolás.
    
    Detalles del pedido:
    - ID del Pedido: #{pedido_id}
    - Cliente: {cliente}
    - Teléfono: {telefono}
    - Dirección: {direccion}
    - Total a cobrar: Q{total:.2f}
    
    Revisa el panel de administración para ver los detalles completos y el comprobante de pago.
    """
    
    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo, 'plain'))
    
    try:
        # Configuración para Gmail (Puerto 587)
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.sendmail(remitente, destinatario, msg.as_string())
        servidor.quit()
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False

# ==========================================
# CONFIGURACIÓN DE QPAYPRO (Producción / Empresa)
# ==========================================
QPAYPRO_API_URL = "https://api-sandboxpayments.qpaypro.com/api/v1/checkout"

X_LOGIN = "AQUI_TU_X_LOGIN"
X_PRIVATE_KEY = "AQUI_TU_X_PRIVATE_KEY"
X_API_SECRET = "AQUI_TU_X_API_SECRET"

class PagoQPayProRequest(BaseModel):
    amount: float
    customer_name: str
    customer_email: str
    card_number: Optional[str] = None

@app.post("/api/create-payment-intent")
def crear_pago_qpaypro(data: PagoQPayProRequest):
    headers = {
        "Content-Type": "application/json",
        "x-login": X_LOGIN,
        "x-private-key": X_PRIVATE_KEY,
        "x-api-secret": X_API_SECRET
    }
    
    payload = {
        "amount": data.amount,
        "nombre": data.customer_name,
        "email": data.customer_email
    }

    try:
        response = requests.post(QPAYPRO_API_URL, json=payload, headers=headers)
        if response.status_code not in [200, 201]:
            raise HTTPException(status_code=400, detail="Error al procesar el pago con QPayPro")
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS Y RUTAS
# ==========================================
imagenes_dir = os.path.join(BASE_DIR, "..", "imagenes")
if os.path.exists(imagenes_dir):
    app.mount("/static/imagenes", StaticFiles(directory=imagenes_dir), name="imagenes_externas")

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

frontend_dir = os.path.join(BASE_DIR, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def leer_index():
    index_path = os.path.join(BASE_DIR, "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    index_raiz = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_raiz):
        return FileResponse(index_raiz)
    return {"mensaje": "Error: No se encontró index.html"}

@app.get("/admin")
def leer_admin():
    admin_path = os.path.join(BASE_DIR, "frontend", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    admin_raiz = os.path.join(BASE_DIR, "..", "frontend", "admin.html")
    if os.path.exists(admin_raiz):
        return FileResponse(admin_raiz)
    return {"mensaje": "Error: No se encontró admin.html"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# MODELOS Y BASE DE DATOS
# ==========================================
class PaymentSchema(BaseModel):
    order_id: int
    client: str
    method: str
    amount: float
    status: Optional[str] = "Completado"
    receipt_url: Optional[str] = None
    invoice_name: Optional[str] = "C/F"
    invoice_nit: Optional[str] = "C/F"
    invoice_number: Optional[str] = "Pendiente"
    invoice_address: Optional[str] = "No especificada"

class LoginRequest(BaseModel):
    username: str
    password: str

def get_db_connection():
    conn = sqlite3.connect("tienda.db")
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_base_datos():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            description TEXT,
            image_url TEXT,
            specs TEXT
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN specs TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT,
            total REAL NOT NULL,
            items TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            invoice_name TEXT DEFAULT 'C/F',
            invoice_nit TEXT DEFAULT 'C/F',
            invoice_number TEXT DEFAULT 'Pendiente',
            invoice_address TEXT DEFAULT 'No especificada',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            client TEXT,
            method TEXT,
            amount REAL,
            status TEXT,
            receipt_url TEXT,
            invoice_name TEXT DEFAULT 'C/F',
            invoice_nit TEXT DEFAULT 'C/F',
            invoice_number TEXT DEFAULT 'Pendiente',
            invoice_address TEXT DEFAULT 'No especificada',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

inicializar_base_datos()

# ==========================================
# RUTAS DE AUTENTICACIÓN ADMINISTRATIVA
# ==========================================
@app.post("/api/admin/login")
def admin_login(data: LoginRequest):
    if data.username == "admind" and data.password == "DON-NICOLAS.03@GT":
        return {"success": True, "message": "Autenticación exitosa"}
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

# ==========================================
# RUTAS DE ADMINISTRACIÓN Y PRODUCTOS
# ==========================================
@app.get("/api/admin/stats")
def obtener_estadisticas():
    inicializar_base_datos()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM products")
    total_productos = cursor.fetchone()[0]
    
    try:
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_pedidos = cursor.fetchone()[0]
    except:
        total_pedidos = 0

    try:
        cursor.execute("SELECT SUM(total) FROM orders")
        res_ingresos = cursor.fetchone()[0]
        ingresos_totales = res_ingresos if res_ingresos else 0.0
    except:
        ingresos_totales = 0.0

    conn.close()
    return {
        "total_productos": total_productos,
        "total_pedidos": total_pedidos,
        "ingresos_totales": ingresos_totales
    }

@app.get("/api/admin/products")
def listar_productos():
    inicializar_base_datos()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos

@app.post("/api/admin/products")
async def crear_producto(
    name: str = Form(...),
    category: str = Form(...),
    price: str = Form(...),
    stock: str = Form(...),
    description: Optional[str] = Form(""),
    specs: Optional[str] = Form(None),
    image: UploadFile = File(None)
):
    try:
        price_val = float(price)
        stock_val = int(stock)
    except ValueError:
        raise HTTPException(status_code=400, detail="El precio debe ser un número válido y el stock un número entero.")

    inicializar_base_datos()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    image_url = "/uploads/cafe-bourbon.jpg"
    try:
        if image and image.filename:
            file_location = os.path.join(UPLOADS_DIR, image.filename)
            with open(file_location, "wb+") as file_object:
                file_object.write(await image.read())
            image_url = f"/uploads/{image.filename}"

        cursor.execute(
            "INSERT INTO products (name, category, price, stock, description, image_url, specs) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, category, price_val, stock_val, description, image_url, specs)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {str(e)}")
        
    conn.close()
    return {"message": "Producto creado con éxito", "id": nuevo_id, "image_url": image_url}

@app.put("/api/admin/products/{producto_id}")
async def actualizar_producto(
    producto_id: int,
    name: str = Form(...),
    category: str = Form(...),
    price: str = Form(...),
    stock: str = Form(...),
    description: Optional[str] = Form(""),
    specs: Optional[str] = Form(None),
    image: UploadFile = File(None)
):
    try:
        price_val = float(price)
        stock_val = int(stock)
    except ValueError:
        raise HTTPException(status_code=400, detail="El precio debe ser un número válido y el stock un número entero.")

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if image and image.filename:
            file_location = os.path.join(UPLOADS_DIR, image.filename)
            with open(file_location, "wb+") as file_object:
                file_object.write(await image.read())
            image_url = f"/uploads/{image.filename}"
            
            cursor.execute(
                "UPDATE products SET name = ?, category = ?, price = ?, stock = ?, description = ?, image_url = ?, specs = ? WHERE id = ?",
                (name, category, price_val, stock_val, description, image_url, specs, producto_id)
            )
        else:
            cursor.execute(
                "UPDATE products SET name = ?, category = ?, price = ?, stock = ?, description = ?, specs = ? WHERE id = ?",
                (name, category, price_val, stock_val, description, specs, producto_id)
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
        
    conn.close()
    return {"message": "Producto actualizado con éxito"}

@app.delete("/api/admin/products/{producto_id}")
def eliminar_producto(producto_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    return {"message": "Producto eliminado con éxito"}

# ==========================================
# GESTIÓN DE PEDIDOS Y PAGOS
# ==========================================
@app.post("/api/orders")
async def crear_pedido_cliente(
    customer: str = Form("Cliente General"),
    total: float = Form(...),
    items: Optional[str] = Form(None),
    phone: Optional[str] = Form(""),
    email: Optional[str] = Form(""),
    address: Optional[str] = Form(""),
    payment_method_type: Optional[str] = Form("Transferencia Bancaria"),
    invoice_name: Optional[str] = Form("C/F"),
    invoice_nit: Optional[str] = Form("C/F"),
    nit: Optional[str] = Form(None),
    invoice_number: Optional[str] = Form("Pendiente"),
    invoice_address: Optional[str] = Form("No especificada"),
    receipt: UploadFile = File(None)
):
    nit_final = nit if nit and nit.strip() != "" else invoice_nit
    if not nit_final:
        nit_final = "C/F"

    inicializar_base_datos()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        receipt_url = None
        if receipt:
            file_location = os.path.join(UPLOADS_DIR, receipt.filename)
            with open(file_location, "wb+") as file_object:
                file_object.write(await receipt.read())
            receipt_url = f"/uploads/{receipt.filename}"

        cursor.execute(
            """INSERT INTO orders 
               (customer, total, items, phone, email, address, invoice_name, invoice_nit, invoice_number, invoice_address) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (customer, total, items, phone, email, address, invoice_name, nit_final, invoice_number, invoice_address)
        )
        conn.commit()
        pedido_id = cursor.lastrowid

        cursor.execute(
            """INSERT INTO payments 
               (order_id, client, method, amount, status, receipt_url, invoice_name, invoice_nit, invoice_number, invoice_address) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pedido_id, customer, payment_method_type, total, "Completado", receipt_url, invoice_name, nit_final, invoice_number, invoice_address)
        )
        conn.commit()

        # Enviar notificación automática por Correo Electrónico[cite: 7]
        enviar_alerta_correo(pedido_id, customer, total, phone, address)

    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
        
    conn.close()
    return {"message": "Pedido y comprobante de pago registrado con éxito", "id": pedido_id, "receipt_url": receipt_url}

@app.get("/api/admin/orders")
def listar_pedidos():
    inicializar_base_datos()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM orders")
        filas = cursor.fetchall()
        pedidos = []
        for row in filas:
            pedido_dict = dict(row)
            pedido_dict["invoice_name"] = row["invoice_name"] if "invoice_name" in row.keys() and row["invoice_name"] else "C/F"
            pedido_dict["invoice_nit"] = row["invoice_nit"] if "invoice_nit" in row.keys() and row["invoice_nit"] else "C/F"
            pedido_dict["invoice_number"] = row["invoice_number"] if "invoice_number" in row.keys() and row["invoice_number"] else "Pendiente"
            pedido_dict["invoice_address"] = row["invoice_address"] if "invoice_address" in row.keys() and row["invoice_address"] else "No especificada"
            pedidos.append(pedido_dict)
    except Exception:
        pedidos = []
    conn.close()
    return pedidos

@app.get("/api/admin/payments")
def listar_pagos():
    inicializar_base_datos()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM payments")
        filas = cursor.fetchall()
        pagos = []
        for row in filas:
            pago_dict = dict(row)
            pago_dict["invoice_name"] = row["invoice_name"] if "invoice_name" in row.keys() and row["invoice_name"] else "C/F"
            pago_dict["invoice_nit"] = row["invoice_nit"] if "invoice_nit`" in row.keys() and row["invoice_nit"] else "C/F"
            pago_dict["invoice_number"] = row["invoice_number"] if "invoice_number" in row.keys() and row["invoice_number"] else "Pendiente"
            pago_dict["invoice_address"] = row["invoice_address"] if "invoice_address" in row.keys() and row["invoice_address"] else "No especificada"
            pagos.append(pago_dict)
    except Exception as e:
        pagos = []
    conn.close()
    return pagos

@app.post("/api/admin/payments")
def registrar_pago(payment: PaymentSchema):
    inicializar_base_datos()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO payments 
               (order_id, client, method, amount, status, receipt_url, invoice_name, invoice_nit, invoice_number, invoice_address) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (payment.order_id, payment.client, payment.method, payment.amount, payment.status, payment.receipt_url, payment.invoice_name, payment.invoice_nit, payment.invoice_number, payment.invoice_address)
        )
        conn.commit()
        pago_id = cursor.lastrowid
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
        
    conn.close()
    return {"message": "Pago registrado con éxito", "id": pago_id}
