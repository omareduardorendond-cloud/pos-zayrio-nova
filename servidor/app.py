from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "clave_secreta_pos_gorras_ropa"
DB_NAME = "pos_sistema.db"

# Código de autorización obligatorio para registrar nuevos usuarios
CODIGO_AUTORIZACION = "Miku7722"

def init_db():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    cursor = conn.cursor()
    
    # Tabla de Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    # Tabla de Productos con campo 'codigo' (SKU)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT DEFAULT 'Gorras',
            precio REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    
    # Tabla de Ventas (Auditoría)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendedor TEXT NOT NULL,
            total REAL NOT NULL,
            dispositivo TEXT DEFAULT 'Web / Móvil',
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    
    # Garantizar que exista el usuario administrador principal
    cursor.execute("DELETE FROM usuarios WHERE username = ?", ("772296 Omar7722",))
    cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", 
                   ("772296 Omar7722", "Omar7722"))
    conn.commit()
    conn.close()

# Inicializar la base de datos al arrancar
init_db()

# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username', '').strip()
        passwd = request.form.get('password', '').strip()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", (user, passwd))
        usuario = cursor.fetchone()
        conn.close()
        
        if usuario:
            session['usuario'] = user
            return redirect(url_for('dashboard'))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nuevo_usuario = request.form.get('username', '').strip()
        nueva_pass = request.form.get('password', '').strip()
        codigo_ingresado = request.form.get('codigo_auth', '').strip()
        
        if codigo_ingresado != CODIGO_AUTORIZACION:
            flash("Código de autorización incorrecto. Registro rechazado.", "danger")
            return redirect(url_for('registro'))
            
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", (nuevo_usuario, nueva_pass))
            conn.commit()
            conn.close()
            flash("¡Usuario registrado con éxito! Ya puedes iniciar sesión.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("El nombre de usuario ya existe.", "danger")
            return redirect(url_for('registro'))
            
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('login'))

# --- PANEL PRINCIPAL Y OPERACIONES ---

@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    busqueda = request.args.get('q', '').strip()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if busqueda:
        cursor.execute("""
            SELECT id, codigo, nombre, categoria, precio, stock 
            FROM productos 
            WHERE nombre LIKE ? OR codigo LIKE ? 
            ORDER BY id DESC
        """, (f'%{busqueda}%', f'%{busqueda}%'))
    else:
        cursor.execute("SELECT id, codigo, nombre, categoria, precio, stock FROM productos ORDER BY id DESC")
        
    productos = cursor.fetchall()
    
    cursor.execute("SELECT id, vendedor, total, dispositivo, fecha FROM ventas ORDER BY id DESC LIMIT 15")
    ventas = cursor.fetchall()
    conn.close()
    
    return render_template('index.html', productos=productos, ventas=ventas, usuario=session['usuario'], busqueda=busqueda)

@app.route('/agregar', methods=['POST'])
def agregar_producto():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    codigo = request.form.get('codigo', '').strip()
    nombre = request.form.get('nombre', '').strip()
    categoria = request.form.get('categoria', 'Gorras')
    precio = float(request.form.get('precio', 0.0))
    stock = int(request.form.get('stock', 0))
    
    if codigo and nombre and precio >= 0:
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO productos (codigo, nombre, categoria, precio, stock) VALUES (?, ?, ?, ?, ?)",
                           (codigo, nombre, categoria, precio, stock))
            conn.commit()
            conn.close()
            flash("Mercancía agregada correctamente al inventario.", "success")
        except sqlite3.IntegrityError:
            flash("El código de producto ya existe. Usa uno diferente.", "danger")
        
    return redirect(url_for('dashboard'))

@app.route('/vender/<int:producto_id>', methods=['POST'])
def registrar_venta(producto_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    vendedor_actual = session['usuario']
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT precio, stock FROM productos WHERE id = ?", (producto_id,))
    prod = cursor.fetchone()
    
    if prod and prod[1] > 0:
        precio = prod[0]
        cursor.execute("INSERT INTO ventas (vendedor, total, dispositivo) VALUES (?, ?, ?)", 
                       (vendedor_actual, precio, "Terminal Web/Móvil"))
        cursor.execute("UPDATE productos SET stock = stock - 1 WHERE id = ?", (producto_id,))
        conn.commit()
        flash("¡Venta registrada con éxito!", "success")
    else:
        flash("No hay suficiente stock de este producto.", "danger")
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_producto(producto_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    flash("Artículo eliminado del inventario correctamente.", "warning")
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)