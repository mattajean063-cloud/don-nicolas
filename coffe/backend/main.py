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

# Configuración correcta de Supabase (sin la barra / al final para evitar errores de ruta)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wrcuytrjherblpiyjlqj.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndyY3V5dHJqaGVyYmxwaXlqbHFqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY0OTgwNDcsImV4cCI6MjEwMjA3NDA0N30.r-EwejBxsAzSgIyE39HieUqHo36Cpya__dNl--gg4WM")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Estado global para control de pasarela de pago con tarjeta
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

class OrderStatusUpdate(BaseModel):
    status: str

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

@app.get("/api/admin/card-payment-status")
def obtener_estado_tarjeta():
    return {"enabled": configuracion_tienda["card_payment_enabled"]}

@app.post("/api/admin/card-payment-status")
def actualizar_estado_tarjeta(data: CardStatusUpdate):
    configuracion_tienda["card_payment_enabled"] = data.enabled
    return {"success": True, "enabled": configuracion_tienda["card_payment_enabled"]}

@app.get("/api/shop/config")
def obtener_configuracion_tienda():
    return {"card_payment_enabled": configuracion_tienda["card_payment_enabled"]}

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

# ENDPOINT CORREGIDO: Soluciona el error 404 al registrar pedidos y activa las notificaciones
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

    receipt_url = None
    if receipt and receipt.filename:
        file_location = os.path.join(UPLOADS_DIR, receipt.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(await receipt.read())
        receipt_url = f"/uploads/{receipt.filename}"

    try:
        nuevo_pedido = {
            "customer": customer,
            "total": total,
            "items": items,
            "phone": phone,
            "email": email,
            "address": address,
            "status": "pendiente",
            "invoice_name": invoice_name,
            "invoice_nit": nit_final,
            "invoice_number": invoice_number,
            "invoice_address": invoice_address
        }
        res_order = supabase.table("orders").insert(nuevo_pedido).execute()
        
        pedido_id = None
        if res_order.data and len(res_order.data) > 0:
            pedido_id = res_order.data[0].get("id")

        nuevo_pago = {
            "order_id": pedido_id,
            "client": customer,
            "method": payment_method_type,
            "amount": total,
            "status": "Completado",
            "receipt_url": receipt_url,
            "invoice_name": invoice_name,
            "invoice_nit": nit_final,
            "invoice_number": invoice_number,
            "invoice_address": invoice_address
        }
        supabase.table("payments").insert(nuevo_pago).execute()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Pedido y comprobante de pago registrado con éxito", "id": pedido_id, "receipt_url": receipt_url}

@app.get("/api/admin/orders")
def listar_pedidos():
    response = supabase.table("orders").select("*").execute()
    return response.data

@app.patch("/api/admin/orders/{pedido_id}/status")
def actualizar_estado_pedido(pedido_id: int, data: OrderStatusUpdate):
    try:
        supabase.table("orders").update({"status": data.status}).eq("id", pedido_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "message": "Estado del pedido actualizado correctamente"}

@app.get("/api/admin/payments")
def listar_pagos():
    response = supabase.table("payments").select("*").execute()
    return response.data
