const API_URL = "";

// Forzar la ejecución absoluta hasta que toda la ventana e imágenes estén listas
window.onload = function() {
    cargarProductosCliente();
    if (document.getElementById("admin-tabla-productos")) {
        cargarProductosAdmin();
        cargarEstadisticasAdmin();
    }
};

async function cargarProductosCliente() {
    try {
        const response = await fetch(`${API_URL}/api/admin/products`);
        const productos = await response.json();
        
        // Buscar de forma amplia cualquier contenedor de productos en tu index.html
        const contenedores = document.querySelectorAll("#catalogo-inicio, #catalogo-tienda, #productos-container, #menu-container, .productos-grid");
        
        if (!contenedores || contenedores.length === 0) {
            console.warn("No se encontró ningún contenedor de catálogo en el HTML.");
            return;
        }

        contenedores.forEach(contenedor => {
            contenedor.innerHTML = ""; // Limpia el texto de "Cargando..."
            
            if (!productos || productos.length === 0) {
                contenedor.innerHTML = "<p style='text-align: center; color: #fff; grid-column: 1 / -1;'>No hay productos disponibles.</p>";
                return;
            }

            productos.forEach(producto => {
                const imagenSrc = `/static/imagenes/${producto.image_url || 'cafe-bourbon.jpg'}`;
                
                const itemHTML = `
                    <div class="producto-card" style="background: rgba(0,0,0,0.6); padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #d4af37; margin-bottom: 15px;">
                        <img src="${imagenSrc}" alt="${producto.name}" style="width:100%; height:150px; object-fit:cover; border-radius:8px;" onerror="this.src='/static/cafe-bourbon.jpg'">
                        <h3 style="color: #f39c12; margin-top: 10px; text-transform: uppercase;">${producto.name}</h3>
                        <p style="color: #ddd; font-size: 0.9rem;">${producto.description || ''}</p>
                        <p class="precio" style="color: #27ae60; font-weight: bold; font-size: 1.1rem;">$${producto.price.toFixed(2)}</p>
                        <button onclick="agregarAlCarrito(${producto.id}, '${producto.name}', ${producto.price})" style="background: #d4af37; color: #000; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 10px;">Agregar al Carrito</button>
                    </div>
                `;
                contenedor.innerHTML += itemHTML;
            });
        });
    } catch (error) {
        console.error("Error al cargar productos:", error);
    }
}

async function cargarEstadisticasAdmin() {
    try {
        const response = await fetch(`${API_URL}/api/admin/stats`);
        const stats = await response.json();
        if (document.getElementById("stat-productos")) document.getElementById("stat-productos").innerText = stats.total_productos;
        if (document.getElementById("stat-pedidos")) document.getElementById("stat-pedidos").innerText = stats.total_pedidos;
        if (document.getElementById("stat-ingresos")) document.getElementById("stat-ingresos").innerText = `$${stats.ingresos_totales.toFixed(2)}`;
    } catch (error) {
        console.error("Error al cargar estadísticas:", error);
    }
}

async function cargarProductosAdmin() {
    try {
        const response = await fetch(`${API_URL}/api/admin/products`);
        const productos = await response.json();
        const tabla = document.getElementById("admin-tabla-productos");
        if (!tabla) return;
        tabla.innerHTML = "";
        productos.forEach(producto => {
            tabla.innerHTML += `
                <tr>
                    <td>${producto.id}</td>
                    <td>${producto.name}</td>
                    <td>${producto.category}</td>
                    <td>$${producto.price.toFixed(2)}</td>
                    <td>${producto.stock}</td>
                    <td><button onclick="eliminarProducto(${producto.id})">Eliminar</button></td>
                </tr>
            `;
        });
    } catch (error) {
        console.error("Error al cargar productos de admin:", error);
    }
}

async function eliminarProducto(id) {
    if (!confirm("¿Estás seguro de eliminar este producto?")) return;
    try {
        const response = await fetch(`${API_URL}/api/admin/products/${id}`, { method: 'DELETE' });
        if (response.ok) {
            cargarProductosAdmin();
            cargarEstadisticasAdmin();
        } else {
            alert("Error al eliminar el producto");
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

let carrito = [];
function agregarAlCarrito(id, name, price) {
    const itemEnCarrito = carrito.find(item => item.id === id);
    if (itemEnCarrito) {
        itemEnCarrito.cantidad += 1;
    } else {
        carrito.push({ id, name, price, cantidad: 1 });
    }
    alert(`¡${name} agregado al carrito!`);
}