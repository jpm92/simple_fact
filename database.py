"""
Módulo de base de datos para el Facturador
Gestiona el almacenamiento de clientes, presupuestos, albaranes y facturas
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path


class Database:
    """Gestiona la base de datos SQLite"""
    
    def __init__(self, db_path="facturador.db"):
        self.db_path = db_path
        self.conn = None
        self.conectar()
        self.crear_tablas()
    
    def conectar(self):
        """Establece conexión con la base de datos"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    
    def crear_tablas(self):
        """Crea las tablas necesarias si no existen"""
        cursor = self.conn.cursor()
        
        # Tabla de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                nif TEXT NOT NULL,
                direccion TEXT,
                codigo_postal TEXT,
                ciudad TEXT,
                provincia TEXT,
                email TEXT,
                telefono TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de documentos (presupuestos, albaranes, facturas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,  -- 'presupuesto', 'albaran', 'factura'
                numero TEXT NOT NULL,
                fecha_emision DATE NOT NULL,
                fecha_validez DATE,  -- Para presupuestos
                cliente_id INTEGER,
                cliente_nombre TEXT,
                cliente_nif TEXT,
                cliente_direccion TEXT,
                cliente_cp TEXT,
                cliente_ciudad TEXT,
                cliente_provincia TEXT,
                base_imponible REAL,
                total_iva REAL,
                irpf_porcentaje REAL DEFAULT 0,
                total_irpf REAL DEFAULT 0,
                total REAL,
                metodo_pago TEXT,
                estado TEXT DEFAULT 'pendiente',  -- 'pendiente', 'aceptado', 'rechazado', 'facturado', 'pagado'
                documento_origen_id INTEGER,  -- ID del presupuesto/albarán del que procede
                notas TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ruta_pdf TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (documento_origen_id) REFERENCES documentos(id)
            )
        ''')
        
        # Migración: añadir columna ruta_pdf si no existe
        try:
            cursor.execute('ALTER TABLE documentos ADD COLUMN ruta_pdf TEXT')
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # La columna ya existe
        
        # Tabla de items/líneas de documento
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documento_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                documento_id INTEGER NOT NULL,
                descripcion TEXT NOT NULL,
                cantidad REAL NOT NULL,
                unidad TEXT DEFAULT 'unidad',  -- 'unidad', 'hora', 'servicio', 'kg', etc.
                precio_unitario REAL NOT NULL,
                iva_porcentaje REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (documento_id) REFERENCES documentos(id) ON DELETE CASCADE
            )
        ''')
        
        # Tabla para series de numeración
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,  -- 'presupuesto', 'albaran', 'factura'
                serie TEXT NOT NULL,
                ultimo_numero INTEGER DEFAULT 0,
                año INTEGER NOT NULL,
                UNIQUE(tipo, serie, año)
            )
        ''')
        
        self.conn.commit()
    
    # === CLIENTES ===
    
    def guardar_cliente(self, cliente_data):
        """Guarda o actualiza un cliente"""
        cursor = self.conn.cursor()
        
        # Buscar si existe por NIF
        cursor.execute('SELECT id FROM clientes WHERE nif = ?', (cliente_data['nif'],))
        existente = cursor.fetchone()
        
        if existente:
            cursor.execute('''
                UPDATE clientes SET 
                    nombre = ?, direccion = ?, codigo_postal = ?,
                    ciudad = ?, provincia = ?, email = ?, telefono = ?
                WHERE id = ?
            ''', (
                cliente_data['nombre'], cliente_data.get('direccion', ''),
                cliente_data.get('codigo_postal', ''), cliente_data.get('ciudad', ''),
                cliente_data.get('provincia', ''), cliente_data.get('email', ''),
                cliente_data.get('telefono', ''), existente['id']
            ))
            cliente_id = existente['id']
        else:
            cursor.execute('''
                INSERT INTO clientes (nombre, nif, direccion, codigo_postal, ciudad, provincia, email, telefono)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cliente_data['nombre'], cliente_data['nif'],
                cliente_data.get('direccion', ''), cliente_data.get('codigo_postal', ''),
                cliente_data.get('ciudad', ''), cliente_data.get('provincia', ''),
                cliente_data.get('email', ''), cliente_data.get('telefono', '')
            ))
            cliente_id = cursor.lastrowid
        
        self.conn.commit()
        return cliente_id
    
    def obtener_clientes(self):
        """Obtiene todos los clientes"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM clientes ORDER BY nombre')
        return [dict(row) for row in cursor.fetchall()]
    
    def obtener_cliente(self, cliente_id):
        """Obtiene un cliente por ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def buscar_cliente_por_nif(self, nif):
        """Busca un cliente por NIF"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM clientes WHERE nif = ?', (nif,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # === SERIES Y NUMERACIÓN ===
    
    def obtener_siguiente_numero(self, tipo, serie):
        """Obtiene el siguiente número para un tipo de documento y serie"""
        cursor = self.conn.cursor()
        año_actual = datetime.now().year
        
        cursor.execute('''
            SELECT ultimo_numero FROM series 
            WHERE tipo = ? AND serie = ? AND año = ?
        ''', (tipo, serie, año_actual))
        
        row = cursor.fetchone()
        
        if row:
            nuevo_numero = row['ultimo_numero'] + 1
            cursor.execute('''
                UPDATE series SET ultimo_numero = ? 
                WHERE tipo = ? AND serie = ? AND año = ?
            ''', (nuevo_numero, tipo, serie, año_actual))
        else:
            nuevo_numero = 1
            cursor.execute('''
                INSERT INTO series (tipo, serie, ultimo_numero, año)
                VALUES (?, ?, ?, ?)
            ''', (tipo, serie, nuevo_numero, año_actual))
        
        self.conn.commit()
        return nuevo_numero
    
    def generar_numero_documento(self, tipo, serie):
        """Genera número de documento con formato: SERIE-AÑO-NUMERO"""
        prefijos = {
            'presupuesto': 'P',
            'albaran': 'AL',
            'factura': ''
        }
        numero = self.obtener_siguiente_numero(tipo, serie)
        año = datetime.now().year
        prefijo = prefijos.get(tipo, '')
        return f"{prefijo}{serie}-{año}-{numero:04d}"
    
    # === DOCUMENTOS ===
    
    def guardar_documento(self, documento_data, items):
        """Guarda un documento (presupuesto, albarán o factura) con sus items"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO documentos (
                tipo, numero, fecha_emision, fecha_validez, cliente_id,
                cliente_nombre, cliente_nif, cliente_direccion, cliente_cp,
                cliente_ciudad, cliente_provincia, base_imponible, total_iva,
                irpf_porcentaje, total_irpf, total, metodo_pago, estado,
                documento_origen_id, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            documento_data['tipo'],
            documento_data['numero'],
            documento_data['fecha_emision'],
            documento_data.get('fecha_validez'),
            documento_data.get('cliente_id'),
            documento_data['cliente_nombre'],
            documento_data['cliente_nif'],
            documento_data.get('cliente_direccion', ''),
            documento_data.get('cliente_cp', ''),
            documento_data.get('cliente_ciudad', ''),
            documento_data.get('cliente_provincia', ''),
            documento_data['base_imponible'],
            documento_data['total_iva'],
            documento_data.get('irpf_porcentaje', 0),
            documento_data.get('total_irpf', 0),
            documento_data['total'],
            documento_data.get('metodo_pago', ''),
            documento_data.get('estado', 'pendiente'),
            documento_data.get('documento_origen_id'),
            documento_data.get('notas', '')
        ))
        
        documento_id = cursor.lastrowid
        
        # Guardar items
        for item in items:
            cursor.execute('''
                INSERT INTO documento_items (
                    documento_id, descripcion, cantidad, unidad,
                    precio_unitario, iva_porcentaje, subtotal
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                documento_id,
                item['descripcion'],
                item['cantidad'],
                item.get('unidad', 'unidad'),
                item['precio_unitario'],
                item['iva'],
                item['subtotal']
            ))
        
        self.conn.commit()
        return documento_id
    
    def obtener_documento(self, documento_id):
        """Obtiene un documento por ID con sus items"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM documentos WHERE id = ?', (documento_id,))
        doc_row = cursor.fetchone()
        
        if not doc_row:
            return None
        
        documento = dict(doc_row)
        
        cursor.execute('SELECT * FROM documento_items WHERE documento_id = ?', (documento_id,))
        documento['items'] = [dict(row) for row in cursor.fetchall()]
        
        return documento
    
    def obtener_documentos_por_tipo(self, tipo, estado=None):
        """Obtiene documentos filtrados por tipo y opcionalmente estado"""
        cursor = self.conn.cursor()
        
        if estado:
            cursor.execute('''
                SELECT * FROM documentos 
                WHERE tipo = ? AND estado = ?
                ORDER BY fecha_emision DESC
            ''', (tipo, estado))
        else:
            cursor.execute('''
                SELECT * FROM documentos 
                WHERE tipo = ?
                ORDER BY fecha_emision DESC
            ''', (tipo,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def actualizar_estado_documento(self, documento_id, nuevo_estado):
        """Actualiza el estado de un documento"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE documentos SET estado = ? WHERE id = ?
        ''', (nuevo_estado, documento_id))
        self.conn.commit()
    
    def actualizar_ruta_pdf(self, documento_id, ruta_pdf):
        """Guarda la ruta del PDF generado para un documento"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE documentos SET ruta_pdf = ? WHERE id = ?
        ''', (ruta_pdf, documento_id))
        self.conn.commit()
    
    def obtener_documentos_pendientes_facturar(self):
        """Obtiene presupuestos aceptados y albaranes pendientes de facturar"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM documentos 
            WHERE (tipo = 'presupuesto' AND estado = 'aceptado')
               OR (tipo = 'albaran' AND estado = 'pendiente')
            ORDER BY fecha_emision DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def cerrar(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
