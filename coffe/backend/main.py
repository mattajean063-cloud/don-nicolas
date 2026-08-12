from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
from typing import Optional
from supabase import create_client, Client

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Credenciales directas o mediante variables de entorno de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wrcuytrjherblpiyjlqj.supabase.co/rest/v1/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndyY3V5dHJqaGVyYmxwaXlqbHFqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY0OTgwNDcsImV4cCI6MjEwMjA3NDA0N30.r-EwejBxsAzSgIyE39HieUqHo36Cpya__dNl--gg4WM")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Estado global para control de tarjeta
configuracion_tienda = {
    "card_payment_enabled": False
}

QPAYPRO_API_URL = "https://api-sandboxpayments.qpaypro.com/api/v1/checkout"
X_LOGIN = os.getenv("X_LOGIN", "AQUI_TU_X_LOGIN")
X_PRIVATE_KEY = os.getenv("X_PRIVATE_KEY", "AQUI_TU_X_PRIVATE_KEY")
X_API_SECRET = os.getenv("X_API_SECRET", "AQUI_TU_X_API_SECRET")

class PagoQPayProRequest(BaseModel):
    amount: float
    customer_name: str
    customer_email: str
    card_number: Optional[str] = None

class CardStatusUpdate(BaseModel):
    enabled: bool

class LoginRequest(BaseModel):
    username: str
    password: str

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

frontend_dir = os.path.join(BASE_DIR, "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def leer_index():
    index_path = os.path.join(BASE_DIR, "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"mensaje": "Error: No se encontró index.html"}

@app.get("/admin")
def leer_admin():
    admin_path = os.path.join(BASE_DIR, "frontend", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return {"mensaje": "Error: No se encontró admin.html"}

@app.post("/api/admin/login")
def admin_login(data: LoginRequest):
    if data.username == "admind" and data.password == "DON-NICOLAS.03@GT":
        return {"success": True, "message": "Autenticación exitosa"}
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

@app.get("/api/admin/stats")
def obtener_estadisticas():
    try:
        prod_res = supabase.table("products").select("id", count="exact").execute()
        total_productos = prod_res.count if prod_res.count is not None else len(prod_res.data)

        order_res = supabase.table("orders").select("total", count="exact").execute()
        total_pedidos = order_res.count if order_res.count is not None else len(order_res.data)

        ingresos_totales = sum([float(o.get("total", 0)) for o in order_res.data])
    except Exception as e:
        total_productos, total_pedidos, ingresos_totales = 0, 0, 0.0

    return {"total_productos": total_productos, "total_pedidos": total_pedidos, "ingresos_totales": ingresos_totales}

@app.get("/api/admin/products")
def listar_productos():
    response = supabase.table("products").select("*").execute()
    return response.data

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
        raise HTTPException(status_code=400, detail="Precio o stock inválido.")

    image_url = "/uploads/cafe-bourbon.jpg"
    if image and image.filename:
        file_location = os.path.join(UPLOADS_DIR, image.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(await image.read())
        image_url = f"/uploads/{image.filename}"

    nuevo_producto = {
        "name": name,
        "category": category,
        "price": price_val,
        "stock": stock_val,
        "description": description,
        "image_url": image_url,
        "specs": specs
    }

    response = supabase.table("products").insert(nuevo_producto).execute()
    return {"message": "Producto creado con éxito", "data": response.data}

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
        raise HTTPException(status_code=400, detail="Precio o stock inválido.")

    datos_actualizados = {
        "name": name,
        "category": category,
        "price": price_val,
        "stock": stock_val,
        "description": description,
        "specs": specs
    }

    if image and image.filename:
        file_location = os.path.join(UPLOADS_DIR, image.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(await image.read())
        datos_actualizados["image_url"] = f"/uploads/{image.filename}"

    response = supabase.table("products").update(datos_actualizados).eq("id", producto_id).execute()
    return {"message": "Producto actualizado con éxito", "data": response.data}

@app.delete("/api/admin/products/{producto_id}")
def eliminar_producto(producto_id: int):
    supabase.table("products").delete().eq("id", producto_id).execute()
    return {"message": "Producto eliminado con éxito"}

@app.get("/api/admin/orders")
def listar_pedidos():
    response = supabase.table("orders").select("*").execute()
    return response.data

@app.get("/api/admin/payments")
def listar_pagos():
    response = supabase.table("payments").select("*").execute()
    return response.data
