"""
Módulo de base de datos para el Facturador
Modelo basado en VENTAS: cada venta agrupa presupuesto, albarán y factura.
"""

import sqlite3
import os
from datetime import datetime


class Database:
    """Gestiona la base de datos SQLite con modelo de Ventas"""
    
    # Estados posibles de una venta (orden de progresión)
    ESTADOS = ['borrador', 'presupuestado', 'aceptado', 'albaranado', 'facturado', 'pagado']
    
    def __init__(self, db_path="facturador.db"):
        self.db_path = db_path
        self.conn = None
        self.conectar()
        self.crear_tablas()
    
    def conectar(self):
        """Establece conexión con la base de datos"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
    
    def crear_tablas(self):
        """Crea las tablas del modelo de Ventas"""
        cursor = self.conn.cursor()
        
        # Tabla de clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                nif TEXT NOT NULL UNIQUE,
                direccion TEXT,
                codigo_postal TEXT,
                ciudad TEXT,
                provincia TEXT,
                email TEXT,
                telefono TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla principal: VENTAS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL,
                cliente_nombre TEXT NOT NULL,
                cliente_nif TEXT NOT NULL,
                cliente_direccion TEXT DEFAULT '',
                cliente_cp TEXT DEFAULT '',
                cliente_ciudad TEXT DEFAULT '',
                cliente_provincia TEXT DEFAULT '',
                base_imponible REAL NOT NULL,
                total_iva REAL NOT NULL,
                irpf_porcentaje REAL DEFAULT 0,
                total_irpf REAL DEFAULT 0,
                total REAL NOT NULL,
                metodo_pago TEXT DEFAULT '',
                notas TEXT DEFAULT '',
                estado TEXT DEFAULT 'borrador',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id)
            )
        ''')
        
        # Items de la venta (compartidos por todos los documentos)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS venta_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL,
                descripcion TEXT NOT NULL,
                cantidad REAL NOT NULL,
                unidad TEXT DEFAULT 'unidad',
                precio_unitario REAL NOT NULL,
                iva_porcentaje REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
            )
        ''')
        
        # Documentos generados para cada venta (presupuesto, albarán, factura)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                numero TEXT NOT NULL,
                fecha_emision TEXT NOT NULL,
                fecha_validez TEXT,
                ruta_pdf TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
            )
        ''')
        
        # Series de numeración
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
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
        """Genera número de documento con formato: PREFIJO+SERIE-AÑO-NUMERO"""
        prefijos = {
            'presupuesto': 'P',
            'albaran': 'AL',
            'factura': ''
        }
        numero = self.obtener_siguiente_numero(tipo, serie)
        año = datetime.now().year
        prefijo = prefijos.get(tipo, '')
        return f"{prefijo}{serie}-{año}-{numero:04d}"
    
    # === VENTAS ===
    
    def crear_venta(self, venta_data, items):
        """Crea una nueva venta con sus items"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO ventas (
                cliente_id, cliente_nombre, cliente_nif, cliente_direccion,
                cliente_cp, cliente_ciudad, cliente_provincia,
                base_imponible, total_iva, irpf_porcentaje, total_irpf,
                total, metodo_pago, notas, estado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            venta_data.get('cliente_id'),
            venta_data['cliente_nombre'],
            venta_data['cliente_nif'],
            venta_data.get('cliente_direccion', ''),
            venta_data.get('cliente_cp', ''),
            venta_data.get('cliente_ciudad', ''),
            venta_data.get('cliente_provincia', ''),
            venta_data['base_imponible'],
            venta_data['total_iva'],
            venta_data.get('irpf_porcentaje', 0),
            venta_data.get('total_irpf', 0),
            venta_data['total'],
            venta_data.get('metodo_pago', ''),
            venta_data.get('notas', ''),
            venta_data.get('estado', 'borrador')
        ))
        
        venta_id = cursor.lastrowid
        
        for item in items:
            cursor.execute('''
                INSERT INTO venta_items (
                    venta_id, descripcion, cantidad, unidad,
                    precio_unitario, iva_porcentaje, subtotal
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                venta_id,
                item['descripcion'],
                item['cantidad'],
                item.get('unidad', 'unidad'),
                item['precio_unitario'],
                item['iva'],
                item['subtotal']
            ))
        
        self.conn.commit()
        return venta_id
    
    def obtener_venta(self, venta_id):
        """Obtiene una venta por ID con items y documentos"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM ventas WHERE id = ?', (venta_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        venta = dict(row)
        
        # Items
        cursor.execute('SELECT * FROM venta_items WHERE venta_id = ?', (venta_id,))
        venta['items'] = [dict(r) for r in cursor.fetchall()]
        
        # Documentos generados (indexados por tipo)
        cursor.execute('SELECT * FROM documentos WHERE venta_id = ? ORDER BY tipo', (venta_id,))
        docs = [dict(r) for r in cursor.fetchall()]
        venta['documentos'] = {d['tipo']: d for d in docs}
        
        return venta
    
    def obtener_ventas(self, estado=None):
        """Obtiene todas las ventas con info de documentos generados"""
        cursor = self.conn.cursor()
        
        query = '''
            SELECT v.*, 
                (SELECT numero FROM documentos WHERE venta_id = v.id AND tipo = 'presupuesto') as num_presupuesto,
                (SELECT numero FROM documentos WHERE venta_id = v.id AND tipo = 'albaran') as num_albaran,
                (SELECT numero FROM documentos WHERE venta_id = v.id AND tipo = 'factura') as num_factura
            FROM ventas v
        '''
        
        if estado:
            query += ' WHERE v.estado = ? ORDER BY v.fecha_creacion DESC'
            cursor.execute(query, (estado,))
        else:
            query += ' ORDER BY v.fecha_creacion DESC'
            cursor.execute(query)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def actualizar_estado_venta(self, venta_id, nuevo_estado):
        """Actualiza el estado de una venta"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE ventas SET estado = ?, fecha_modificacion = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (nuevo_estado, venta_id))
        self.conn.commit()
    
    def eliminar_venta(self, venta_id):
        """Elimina una venta, sus items, documentos y PDFs del disco"""
        cursor = self.conn.cursor()
        
        # Obtener rutas de PDFs para borrarlos del disco
        cursor.execute('SELECT ruta_pdf FROM documentos WHERE venta_id = ?', (venta_id,))
        rutas = [row['ruta_pdf'] for row in cursor.fetchall() if row['ruta_pdf']]
        
        # Borrar de la BD (CASCADE borra items y documentos)
        cursor.execute('DELETE FROM ventas WHERE id = ?', (venta_id,))
        self.conn.commit()
        
        # Borrar PDFs del disco
        for ruta in rutas:
            try:
                if os.path.exists(ruta):
                    os.remove(ruta)
            except OSError:
                pass
    
    # === DOCUMENTOS (PDFs generados para una venta) ===
    
    def registrar_documento(self, venta_id, tipo, numero, fecha_emision, fecha_validez=None, ruta_pdf=None):
        """Registra un documento generado para una venta (o actualiza si ya existe)"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT id FROM documentos WHERE venta_id = ? AND tipo = ?', (venta_id, tipo))
        existente = cursor.fetchone()
        
        if existente:
            cursor.execute('''
                UPDATE documentos SET numero = ?, fecha_emision = ?, fecha_validez = ?, ruta_pdf = ?
                WHERE id = ?
            ''', (numero, fecha_emision, fecha_validez, ruta_pdf, existente['id']))
            doc_id = existente['id']
        else:
            cursor.execute('''
                INSERT INTO documentos (venta_id, tipo, numero, fecha_emision, fecha_validez, ruta_pdf)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (venta_id, tipo, numero, fecha_emision, fecha_validez, ruta_pdf))
            doc_id = cursor.lastrowid
        
        self.conn.commit()
        return doc_id
    
    def obtener_documento_de_venta(self, venta_id, tipo):
        """Obtiene un documento específico de una venta"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM documentos WHERE venta_id = ? AND tipo = ?', (venta_id, tipo))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def cerrar(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
