"""
Software de Facturación para España - Versión 2.0
Gestión completa: Presupuestos → Albaranes → Facturas

Cumple con los requisitos legales según la normativa española vigente (2025)
- Ley 58/2003 General Tributaria
- Real Decreto 1619/2012 (Reglamento de Facturación)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

# Tema moderno para la interfaz
# Nota: ttkthemes está disponible pero los temas nativos de ttk son más rápidos
# Usamos ttk.Style con temas nativos (clam, vista, winnative)

# Módulos propios
from database import Database
from pdf_generator import GeneradorPDF

# Directorio base para documentos generados
DOCUMENTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Documentos")


def obtener_ruta_documento(tipo, numero):
    """Genera la ruta organizada para guardar un PDF.
    
    Estructura: Documentos/<Tipo>/<Año>/<archivo>.pdf
    Ejemplo:    Documentos/Facturas/2026/Factura_A-2026-0001.pdf
    """
    carpetas_tipo = {
        'presupuesto': 'Presupuestos',
        'albaran': 'Albaranes',
        'factura': 'Facturas'
    }
    carpeta = carpetas_tipo.get(tipo, 'Otros')
    año = str(datetime.now().year)
    
    directorio = os.path.join(DOCUMENTOS_DIR, carpeta, año)
    os.makedirs(directorio, exist_ok=True)
    
    nombre_archivo = f"{carpeta[:-1]}_{numero.replace('/', '-')}.pdf"
    return os.path.join(directorio, nombre_archivo)


class ConfigManager:
    """Gestiona la configuración del emisor y facturas"""
    
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.cargar_config()
    
    def cargar_config(self):
        """Carga la configuración desde archivo JSON"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Asegurar campos nuevos
                if 'iban' not in config.get('emisor', {}):
                    config['emisor']['iban'] = ''
                if 'irpf_por_defecto' not in config:
                    config['irpf_por_defecto'] = 0
                if 'serie_presupuesto' not in config:
                    config['serie_presupuesto'] = 'P'
                if 'serie_albaran' not in config:
                    config['serie_albaran'] = 'AL'
                return config
        return self.config_por_defecto()
    
    def config_por_defecto(self):
        """Retorna configuración por defecto"""
        return {
            "emisor": {
                "nombre": "",
                "nif": "",
                "direccion": "",
                "codigo_postal": "",
                "ciudad": "",
                "provincia": "",
                "email": "",
                "telefono": "",
                "iban": ""
            },
            "serie_factura": "A",
            "serie_presupuesto": "P",
            "serie_albaran": "AL",
            "ultimo_numero": 0,
            "iva_por_defecto": 21,
            "irpf_por_defecto": 0
        }
    
    def guardar_config(self):
        """Guarda la configuración en archivo JSON"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)


class VentanaConfiguracion(tk.Toplevel):
    """Ventana para configurar los datos del emisor"""
    
    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.config_manager = config_manager
        self.title("Configuración - Datos del Emisor")
        self.geometry("550x550")
        self.resizable(False, False)
        
        self.crear_widgets()
        self.cargar_datos()
        
        self.transient(parent)
        self.grab_set()
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        # Canvas con scroll
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding="20")
        
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Título
        ttk.Label(frame, text="Datos del Emisor (Tu empresa/autónomo)", 
                  font=('Helvetica', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Campos del emisor
        campos = [
            ("Nombre/Razón Social:", "nombre"),
            ("NIF/CIF:", "nif"),
            ("Dirección:", "direccion"),
            ("Código Postal:", "codigo_postal"),
            ("Ciudad:", "ciudad"),
            ("Provincia:", "provincia"),
            ("Email:", "email"),
            ("Teléfono:", "telefono"),
            ("IBAN (cuenta bancaria):", "iban")
        ]
        
        self.entries = {}
        for i, (label, campo) in enumerate(campos):
            ttk.Label(frame, text=label).grid(row=i+1, column=0, sticky='e', pady=5, padx=5)
            width = 30 if campo != 'iban' else 35
            entry = ttk.Entry(frame, width=width)
            entry.grid(row=i+1, column=1, sticky='w', pady=5)
            self.entries[campo] = entry
        
        # Separador
        ttk.Separator(frame, orient='horizontal').grid(row=len(campos)+1, column=0, columnspan=2, sticky='ew', pady=15)
        
        # Configuración de series
        ttk.Label(frame, text="Configuración de Series y Valores por Defecto", 
                  font=('Helvetica', 10, 'bold')).grid(row=len(campos)+2, column=0, columnspan=2, pady=(0, 10))
        
        row_base = len(campos) + 3
        
        ttk.Label(frame, text="Serie Facturas:").grid(row=row_base, column=0, sticky='e', pady=5, padx=5)
        self.entry_serie_factura = ttk.Entry(frame, width=10)
        self.entry_serie_factura.grid(row=row_base, column=1, sticky='w', pady=5)
        
        ttk.Label(frame, text="Serie Presupuestos:").grid(row=row_base+1, column=0, sticky='e', pady=5, padx=5)
        self.entry_serie_presupuesto = ttk.Entry(frame, width=10)
        self.entry_serie_presupuesto.grid(row=row_base+1, column=1, sticky='w', pady=5)
        
        ttk.Label(frame, text="Serie Albaranes:").grid(row=row_base+2, column=0, sticky='e', pady=5, padx=5)
        self.entry_serie_albaran = ttk.Entry(frame, width=10)
        self.entry_serie_albaran.grid(row=row_base+2, column=1, sticky='w', pady=5)
        
        ttk.Label(frame, text="IVA por defecto (%):").grid(row=row_base+3, column=0, sticky='e', pady=5, padx=5)
        self.entry_iva = ttk.Entry(frame, width=10)
        self.entry_iva.grid(row=row_base+3, column=1, sticky='w', pady=5)
        
        ttk.Label(frame, text="IRPF por defecto (%):").grid(row=row_base+4, column=0, sticky='e', pady=5, padx=5)
        self.entry_irpf = ttk.Entry(frame, width=10)
        self.entry_irpf.grid(row=row_base+4, column=1, sticky='w', pady=5)
        
        # Nota de ayuda en fila separada para evitar overlap
        ttk.Label(frame, text="(Ej: 15 para autónomos, 7 para nuevos autónomos)", 
                  font=('Segoe UI', 8)).grid(row=row_base+5, column=0, columnspan=2, sticky='w', padx=10, pady=(0, 5))
        
        # Botones
        frame_botones = ttk.Frame(frame)
        frame_botones.grid(row=row_base+7, column=0, columnspan=2, pady=20)
        
        ttk.Button(frame_botones, text="Guardar", command=self.guardar).pack(side=tk.LEFT, padx=10)
        ttk.Button(frame_botones, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=10)
    
    def cargar_datos(self):
        """Carga los datos existentes en los campos"""
        emisor = self.config_manager.config.get("emisor", {})
        for campo, entry in self.entries.items():
            valor = emisor.get(campo, "")
            entry.insert(0, valor)
        
        self.entry_serie_factura.insert(0, self.config_manager.config.get("serie_factura", "A"))
        self.entry_serie_presupuesto.insert(0, self.config_manager.config.get("serie_presupuesto", "P"))
        self.entry_serie_albaran.insert(0, self.config_manager.config.get("serie_albaran", "AL"))
        self.entry_iva.insert(0, str(self.config_manager.config.get("iva_por_defecto", 21)))
        self.entry_irpf.insert(0, str(self.config_manager.config.get("irpf_por_defecto", 0)))
    
    def guardar(self):
        """Guarda la configuración"""
        nif = self.entries['nif'].get().strip()
        if not nif:
            messagebox.showerror("Error", "El NIF/CIF es obligatorio")
            return
        
        for campo, entry in self.entries.items():
            self.config_manager.config["emisor"][campo] = entry.get().strip()
        
        self.config_manager.config["serie_factura"] = self.entry_serie_factura.get().strip() or "A"
        self.config_manager.config["serie_presupuesto"] = self.entry_serie_presupuesto.get().strip() or "P"
        self.config_manager.config["serie_albaran"] = self.entry_serie_albaran.get().strip() or "AL"
        
        try:
            self.config_manager.config["iva_por_defecto"] = int(self.entry_iva.get())
        except ValueError:
            self.config_manager.config["iva_por_defecto"] = 21
        
        try:
            self.config_manager.config["irpf_por_defecto"] = int(self.entry_irpf.get())
        except ValueError:
            self.config_manager.config["irpf_por_defecto"] = 0
        
        self.config_manager.guardar_config()
        messagebox.showinfo("Éxito", "Configuración guardada correctamente")
        self.destroy()


class VentanaHistorial(tk.Toplevel):
    """Ventana para ver el historial de documentos"""
    
    def __init__(self, parent, db, tipo_filtro=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.tipo_filtro = tipo_filtro
        
        titulo = "Historial"
        if tipo_filtro:
            titulos = {'presupuesto': 'Presupuestos', 'albaran': 'Albaranes', 'factura': 'Facturas'}
            titulo = f"Historial de {titulos.get(tipo_filtro, tipo_filtro)}"
        
        self.title(titulo)
        self.geometry("900x500")
        
        self.crear_widgets()
        self.cargar_datos()
        
        self.transient(parent)
    
    def crear_widgets(self):
        """Crea los widgets de la ventana"""
        # === FILTROS (arriba) ===
        frame_filtros = ttk.Frame(self, padding=(10, 10, 10, 5))
        frame_filtros.pack(fill=tk.X, side=tk.TOP)
        
        ttk.Label(frame_filtros, text="Tipo:").pack(side=tk.LEFT, padx=5)
        self.combo_tipo = ttk.Combobox(frame_filtros, width=15, 
                                        values=['Todos', 'Presupuesto', 'Albarán', 'Factura'])
        if self.tipo_filtro:
            tipos_map = {'presupuesto': 'Presupuesto', 'albaran': 'Albarán', 'factura': 'Factura'}
            self.combo_tipo.set(tipos_map.get(self.tipo_filtro, 'Todos'))
        else:
            self.combo_tipo.set('Todos')
        self.combo_tipo.pack(side=tk.LEFT, padx=5)
        self.combo_tipo.bind('<<ComboboxSelected>>', lambda e: self.cargar_datos())
        
        ttk.Button(frame_filtros, text="Actualizar", command=self.cargar_datos).pack(side=tk.LEFT, padx=20)
        
        # === BOTONES DE ACCIÓN (abajo) ===
        frame_inferior = ttk.Frame(self, padding=(10, 5, 10, 10))
        frame_inferior.pack(fill=tk.X, side=tk.BOTTOM)
        
        # Nota informativa
        ttk.Label(frame_inferior, text="💡 Doble clic en un documento para ver su PDF", 
                  font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(0, 5))
        
        frame_acciones = ttk.Frame(frame_inferior)
        frame_acciones.pack(fill=tk.X)
        
        ttk.Label(frame_acciones, text="Acciones:", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(frame_acciones, text="📄 Ver PDF", 
                   command=self.generar_pdf).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acciones, text="✅ Aceptar", 
                   command=lambda: self.cambiar_estado('aceptado')).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acciones, text="📦 → Albarán", 
                   command=self.crear_albaran_desde_presupuesto).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acciones, text="🧾 → Factura", 
                   command=self.facturar_documento).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acciones, text="💰 Pagado", 
                   command=lambda: self.cambiar_estado('pagado')).pack(side=tk.LEFT, padx=3)
        
        # === TABLA (centro, ocupa el espacio restante) ===
        frame_tabla = ttk.Frame(self, padding=(10, 0, 10, 0))
        frame_tabla.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        columns = ('tipo', 'numero', 'fecha', 'cliente', 'total', 'estado')
        self.tree = ttk.Treeview(frame_tabla, columns=columns, show='headings', height=15)
        
        self.tree.heading('tipo', text='Tipo')
        self.tree.heading('numero', text='Número')
        self.tree.heading('fecha', text='Fecha')
        self.tree.heading('cliente', text='Cliente')
        self.tree.heading('total', text='Total')
        self.tree.heading('estado', text='Estado')
        
        self.tree.column('tipo', width=100)
        self.tree.column('numero', width=150)
        self.tree.column('fecha', width=100)
        self.tree.column('cliente', width=200)
        self.tree.column('total', width=100, anchor='e')
        self.tree.column('estado', width=100)
        
        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Doble clic para generar PDF
        self.tree.bind('<Double-1>', lambda e: self.generar_pdf())
    
    def cargar_datos(self):
        """Carga los documentos en la tabla"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        tipo_seleccionado = self.combo_tipo.get()
        tipo_map = {'Presupuesto': 'presupuesto', 'Albarán': 'albaran', 'Factura': 'factura'}
        
        if tipo_seleccionado == 'Todos':
            for tipo in ['presupuesto', 'albaran', 'factura']:
                docs = self.db.obtener_documentos_por_tipo(tipo)
                for doc in docs:
                    self.insertar_documento(doc)
        else:
            tipo = tipo_map.get(tipo_seleccionado)
            if tipo:
                docs = self.db.obtener_documentos_por_tipo(tipo)
                for doc in docs:
                    self.insertar_documento(doc)
    
    def insertar_documento(self, doc):
        """Inserta un documento en la tabla"""
        tipos_display = {'presupuesto': '📋 Presupuesto', 'albaran': '📦 Albarán', 'factura': '🧾 Factura'}
        estados_display = {
            'pendiente': '⏳ Pendiente',
            'aceptado': '✅ Aceptado',
            'rechazado': '❌ Rechazado',
            'facturado': '🧾 Facturado',
            'pagado': '💰 Pagado'
        }
        
        self.tree.insert('', tk.END, iid=doc['id'], values=(
            tipos_display.get(doc['tipo'], doc['tipo']),
            doc['numero'],
            doc['fecha_emision'],
            doc['cliente_nombre'],
            f"{doc['total']:.2f} €",
            estados_display.get(doc['estado'], doc['estado'])
        ), tags=(doc['tipo'],))
    
    def obtener_documento_seleccionado(self):
        """Obtiene el documento seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona un documento")
            return None
        return self.db.obtener_documento(int(seleccion[0]))
    
    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado de un documento"""
        doc = self.obtener_documento_seleccionado()
        if doc:
            self.db.actualizar_estado_documento(doc['id'], nuevo_estado)
            self.cargar_datos()
            messagebox.showinfo("Éxito", f"Estado actualizado a: {nuevo_estado}")
    
    def generar_pdf(self):
        """Abre el PDF si ya existe, o lo genera si no"""
        doc = self.obtener_documento_seleccionado()
        if not doc:
            return
        
        # Si ya tiene un PDF guardado y el archivo existe, abrirlo directamente
        ruta_existente = doc.get('ruta_pdf')
        if ruta_existente and os.path.exists(ruta_existente):
            try:
                os.startfile(ruta_existente)
                return
            except Exception:
                pass  # Si falla, continuar para regenerar
        
        # No existe PDF previo: generar uno nuevo
        self._generar_nuevo_pdf(doc)
    
    def _generar_nuevo_pdf(self, doc):
        """Genera un nuevo PDF para el documento"""
        config = self.parent.config_manager.config
        
        items = []
        for item in doc['items']:
            items.append({
                'descripcion': item['descripcion'],
                'cantidad': item['cantidad'],
                'unidad': item.get('unidad', 'unidad'),
                'precio_unitario': item['precio_unitario'],
                'iva': item['iva_porcentaje'],
                'subtotal': item['subtotal']
            })
        
        # Calcular desglose IVA
        desglose_iva = {}
        for item in items:
            tipo = int(item['iva'])
            if tipo not in desglose_iva:
                desglose_iva[tipo] = {'base': 0, 'cuota': 0}
            desglose_iva[tipo]['base'] += item['subtotal']
            desglose_iva[tipo]['cuota'] += item['subtotal'] * tipo / 100
        
        datos_pdf = {
            'tipo': doc['tipo'],
            'numero': doc['numero'],
            'fecha_emision': doc['fecha_emision'],
            'fecha_validez': doc.get('fecha_validez'),
            'emisor': config['emisor'],
            'cliente': {
                'nombre': doc['cliente_nombre'],
                'nif': doc['cliente_nif'],
                'direccion': doc.get('cliente_direccion', ''),
                'codigo_postal': doc.get('cliente_cp', ''),
                'ciudad': doc.get('cliente_ciudad', ''),
                'provincia': doc.get('cliente_provincia', '')
            },
            'items': items,
            'totales': {
                'base_imponible': doc['base_imponible'],
                'total_iva': doc['total_iva'],
                'irpf_porcentaje': doc.get('irpf_porcentaje', 0),
                'total_irpf': doc.get('total_irpf', 0),
                'total': doc['total'],
                'desglose_iva': desglose_iva
            },
            'metodo_pago': doc.get('metodo_pago', ''),
            'notas': doc.get('notas', '')
        }
        
        # Guardar PDF automáticamente en carpeta organizada
        ruta = obtener_ruta_documento(doc['tipo'], doc['numero'])
        
        try:
            generador = GeneradorPDF()
            generador.generar_documento(datos_pdf, ruta)
            
            # Guardar ruta del PDF en la base de datos
            self.db.actualizar_ruta_pdf(doc['id'], ruta)
            
            messagebox.showinfo("Éxito", f"PDF generado:\n{ruta}")
            os.startfile(ruta)
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar PDF:\n{str(e)}")
    
    def crear_albaran_desde_presupuesto(self):
        """Crea un albarán a partir de un presupuesto o documento"""
        doc = self.obtener_documento_seleccionado()
        if not doc:
            return
        
        if doc['tipo'] == 'factura':
            messagebox.showwarning("Aviso", "No se pueden crear albaranes desde facturas")
            return
        
        if doc['tipo'] == 'presupuesto' and doc['estado'] == 'pendiente':
            # Preguntar si quiere aceptarlo primero
            if messagebox.askyesno("Presupuesto pendiente", 
                                   "El presupuesto está pendiente. ¿Deseas marcarlo como aceptado antes de crear el albarán?"):
                self.db.actualizar_estado_documento(doc['id'], 'aceptado')
        
        # Crear albarán
        self.parent.cargar_documento_para_nuevo(doc, 'albaran')
        self.destroy()
    
    def facturar_documento(self):
        """Crea una factura a partir de un presupuesto o albarán"""
        doc = self.obtener_documento_seleccionado()
        if not doc:
            return
        
        if doc['tipo'] == 'factura':
            messagebox.showwarning("Aviso", "Este documento ya es una factura")
            return
        
        if doc['tipo'] == 'presupuesto' and doc['estado'] == 'pendiente':
            # Preguntar si quiere aceptarlo primero
            if messagebox.askyesno("Presupuesto pendiente", 
                                   "El presupuesto está pendiente. ¿Deseas marcarlo como aceptado antes de facturar?"):
                self.db.actualizar_estado_documento(doc['id'], 'aceptado')
            else:
                return
        
        # Crear factura
        self.parent.cargar_documento_para_nuevo(doc, 'factura')
        self.destroy()


class VentanaSeleccionarCliente(tk.Toplevel):
    """Ventana para seleccionar un cliente existente"""
    
    def __init__(self, parent, db):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.cliente_seleccionado = None
        
        self.title("Seleccionar Cliente")
        self.geometry("600x400")
        
        self.crear_widgets()
        self.cargar_clientes()
        
        self.transient(parent)
        self.grab_set()
    
    def crear_widgets(self):
        """Crea los widgets"""
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Búsqueda
        frame_busqueda = ttk.Frame(frame)
        frame_busqueda.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_busqueda, text="Buscar:").pack(side=tk.LEFT, padx=5)
        self.entry_busqueda = ttk.Entry(frame_busqueda, width=30)
        self.entry_busqueda.pack(side=tk.LEFT, padx=5)
        self.entry_busqueda.bind('<KeyRelease>', lambda e: self.filtrar_clientes())
        
        # Lista de clientes
        columns = ('nombre', 'nif', 'ciudad')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=12)
        
        self.tree.heading('nombre', text='Nombre')
        self.tree.heading('nif', text='NIF/CIF')
        self.tree.heading('ciudad', text='Ciudad')
        
        self.tree.column('nombre', width=250)
        self.tree.column('nif', width=120)
        self.tree.column('ciudad', width=150)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<Double-1>', lambda e: self.seleccionar())
        
        # Botones
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_botones, text="Seleccionar", command=self.seleccionar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def cargar_clientes(self):
        """Carga todos los clientes"""
        self.clientes = self.db.obtener_clientes()
        self.mostrar_clientes(self.clientes)
    
    def mostrar_clientes(self, clientes):
        """Muestra los clientes en la tabla"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for cliente in clientes:
            self.tree.insert('', tk.END, iid=cliente['id'], values=(
                cliente['nombre'],
                cliente['nif'],
                cliente.get('ciudad', '')
            ))
    
    def filtrar_clientes(self):
        """Filtra los clientes por texto"""
        texto = self.entry_busqueda.get().lower()
        filtrados = [c for c in self.clientes if 
                     texto in c['nombre'].lower() or 
                     texto in c['nif'].lower()]
        self.mostrar_clientes(filtrados)
    
    def seleccionar(self):
        """Selecciona el cliente y cierra la ventana"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona un cliente")
            return
        
        self.cliente_seleccionado = self.db.obtener_cliente(int(seleccion[0]))
        self.destroy()


class AplicacionFacturador(tk.Tk):
    """Aplicación principal de facturación"""
    
    UNIDADES = ['unidad', 'hora', 'servicio', 'día', 'mes', 'kg', 'm²', 'proyecto']
    
    # Usamos temas nativos de ttk que son rápidos
    # 'clam' es moderno y rápido, disponible en todas las plataformas
    # 'vista'/'winnative' son buenos en Windows pero pueden no estar disponibles
    TEMAS_PREFERIDOS = ['vista', 'winnative', 'clam', 'alt', 'default']
    
    def __init__(self):
        super().__init__()
        
        # Aplicar tema nativo (no usamos ttkthemes, son muy lentos)
        self.aplicar_tema_nativo()
        
        self.title("Facturador España v2.0")
        self.geometry("1000x800")
        
        # Configurar estilos personalizados
        self.configurar_estilos()
        
        # Configuración y base de datos
        self.config_manager = ConfigManager()
        self.db = Database()
        
        # Tipo de documento actual
        self.tipo_documento = tk.StringVar(value='factura')
        
        # Items del documento
        self.items = []
        
        # Documento origen (para flujo presupuesto -> albarán -> factura)
        self.documento_origen_id = None
        self.documento_origen_numero = None
        
        self.crear_menu()
        self.crear_widgets()
    
    def aplicar_tema_nativo(self):
        """Aplica un tema nativo de ttk (rápido y sin dependencias)"""
        style = ttk.Style()
        temas_disponibles = style.theme_names()
        
        for tema in self.TEMAS_PREFERIDOS:
            if tema in temas_disponibles:
                try:
                    style.theme_use(tema)
                    return
                except Exception:
                    continue
        
        # Fallback al tema por defecto
        if 'clam' in temas_disponibles:
            style.theme_use('clam')
    
    def configurar_estilos(self):
        """Configura estilos personalizados para mejorar la apariencia"""
        style = ttk.Style()
        
        # Configurar fuentes más grandes y legibles
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10), padding=6)
        style.configure('TEntry', font=('Segoe UI', 10), padding=4)
        style.configure('TCombobox', font=('Segoe UI', 10))
        style.configure('TRadiobutton', font=('Segoe UI', 10))
        style.configure('TCheckbutton', font=('Segoe UI', 10))
        
        # Estilo para LabelFrames
        style.configure('TLabelframe', font=('Segoe UI', 10, 'bold'))
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        
        # Estilo para el Treeview
        style.configure('Treeview', font=('Segoe UI', 10), rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        
        # Estilo para botones grandes/importantes
        style.configure('Accent.TButton', font=('Segoe UI', 11, 'bold'), padding=10)
        
        # Estilo para etiquetas de título
        style.configure('Title.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Subtitle.TLabel', font=('Segoe UI', 11))
        style.configure('Total.TLabel', font=('Segoe UI', 13, 'bold'))
    
    def crear_menu(self):
        """Crea el menú de la aplicación"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menú Archivo
        menu_archivo = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=menu_archivo)
        menu_archivo.add_command(label="Nuevo Documento", command=self.nuevo_documento)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Salir", command=self.salir)
        
        # Menú Ver
        menu_ver = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ver", menu=menu_ver)
        menu_ver.add_command(label="Todos los documentos", 
                             command=lambda: self.abrir_historial())
        menu_ver.add_separator()
        menu_ver.add_command(label="Presupuestos", 
                             command=lambda: self.abrir_historial('presupuesto'))
        menu_ver.add_command(label="Albaranes", 
                             command=lambda: self.abrir_historial('albaran'))
        menu_ver.add_command(label="Facturas", 
                             command=lambda: self.abrir_historial('factura'))
        menu_ver.add_separator()
        menu_ver.add_command(label="Pendientes de facturar", 
                             command=self.ver_pendientes_facturar)
        
        # Menú Configuración
        menu_config = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=menu_config)
        menu_config.add_command(label="Datos del Emisor", command=self.abrir_configuracion)
    
    def crear_widgets(self):
        """Crea los widgets principales"""
        # Frame principal con scroll
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Selector de tipo de documento ===
        frame_tipo = ttk.LabelFrame(main_frame, text="Tipo de Documento", padding="10")
        frame_tipo.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Radiobutton(frame_tipo, text="📋 Presupuesto", variable=self.tipo_documento, 
                        value='presupuesto').pack(side=tk.LEFT, padx=20)
        ttk.Radiobutton(frame_tipo, text="📦 Albarán", variable=self.tipo_documento, 
                        value='albaran').pack(side=tk.LEFT, padx=20)
        ttk.Radiobutton(frame_tipo, text="🧾 Factura", variable=self.tipo_documento, 
                        value='factura').pack(side=tk.LEFT, padx=20)
        
        # === Sección Cliente ===
        frame_cliente = ttk.LabelFrame(main_frame, text="Datos del Cliente", padding="10")
        frame_cliente.pack(fill=tk.X, pady=(0, 10))
        
        # Botón para seleccionar cliente existente
        frame_cliente_acciones = ttk.Frame(frame_cliente)
        frame_cliente_acciones.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(frame_cliente_acciones, text="📂 Seleccionar Cliente Existente", 
                   command=self.seleccionar_cliente).pack(side=tk.LEFT)
        
        # Grid para datos del cliente
        campos_cliente = [
            ("Nombre/Razón Social:", "nombre"),
            ("NIF/CIF:", "nif"),
            ("Dirección:", "direccion"),
            ("C.P.:", "codigo_postal"),
            ("Ciudad:", "ciudad"),
            ("Provincia:", "provincia")
        ]
        
        frame_campos_cliente = ttk.Frame(frame_cliente)
        frame_campos_cliente.pack(fill=tk.X)
        
        self.cliente_entries = {}
        for i, (label, campo) in enumerate(campos_cliente):
            row = i // 3
            col = (i % 3) * 2
            ttk.Label(frame_campos_cliente, text=label).grid(row=row, column=col, sticky='e', padx=5, pady=5)
            width = 15 if campo in ['codigo_postal', 'nif'] else 25
            entry = ttk.Entry(frame_campos_cliente, width=width)
            entry.grid(row=row, column=col+1, sticky='w', padx=5, pady=5)
            self.cliente_entries[campo] = entry
        
        # === Sección Items ===
        frame_items = ttk.LabelFrame(main_frame, text="Conceptos/Items", padding="10")
        frame_items.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Frame para añadir items
        frame_add_item = ttk.Frame(frame_items)
        frame_add_item.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_add_item, text="Descripción:").grid(row=0, column=0, padx=5, pady=2)
        self.entry_descripcion = ttk.Entry(frame_add_item, width=40)
        self.entry_descripcion.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(frame_add_item, text="Cantidad:").grid(row=0, column=2, padx=5, pady=2)
        self.entry_cantidad = ttk.Entry(frame_add_item, width=8)
        self.entry_cantidad.insert(0, "1")
        self.entry_cantidad.grid(row=0, column=3, padx=5, pady=2)
        
        ttk.Label(frame_add_item, text="Unidad:").grid(row=0, column=4, padx=5, pady=2)
        self.combo_unidad = ttk.Combobox(frame_add_item, width=10, values=self.UNIDADES)
        self.combo_unidad.set('unidad')
        self.combo_unidad.grid(row=0, column=5, padx=5, pady=2)
        
        ttk.Label(frame_add_item, text="Precio (€):").grid(row=1, column=0, padx=5, pady=2)
        self.entry_precio = ttk.Entry(frame_add_item, width=12)
        self.entry_precio.grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Label(frame_add_item, text="IVA (%):").grid(row=1, column=2, padx=5, pady=2)
        self.combo_iva = ttk.Combobox(frame_add_item, width=5, values=['0', '4', '10', '21'])
        self.combo_iva.set(str(self.config_manager.config.get("iva_por_defecto", 21)))
        self.combo_iva.grid(row=1, column=3, padx=5, pady=2)
        
        ttk.Button(frame_add_item, text="➕ Añadir Item", 
                   command=self.añadir_item).grid(row=1, column=5, padx=10, pady=2)
        
        # Tabla de items
        columns = ('descripcion', 'cantidad', 'unidad', 'precio', 'iva', 'subtotal')
        self.tree_items = ttk.Treeview(frame_items, columns=columns, show='headings', height=8)
        
        self.tree_items.heading('descripcion', text='Descripción')
        self.tree_items.heading('cantidad', text='Cantidad')
        self.tree_items.heading('unidad', text='Unidad')
        self.tree_items.heading('precio', text='Precio Unit.')
        self.tree_items.heading('iva', text='IVA %')
        self.tree_items.heading('subtotal', text='Subtotal')
        
        self.tree_items.column('descripcion', width=280)
        self.tree_items.column('cantidad', width=80, anchor='center')
        self.tree_items.column('unidad', width=80, anchor='center')
        self.tree_items.column('precio', width=100, anchor='e')
        self.tree_items.column('iva', width=60, anchor='center')
        self.tree_items.column('subtotal', width=100, anchor='e')
        
        scrollbar = ttk.Scrollbar(frame_items, orient=tk.VERTICAL, command=self.tree_items.yview)
        self.tree_items.configure(yscrollcommand=scrollbar.set)
        
        self.tree_items.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Botón eliminar item
        frame_acciones_items = ttk.Frame(main_frame)
        frame_acciones_items.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(frame_acciones_items, text="🗑️ Eliminar Item Seleccionado", 
                   command=self.eliminar_item).pack(side=tk.LEFT)
        
        # === Sección IRPF y Totales ===
        frame_totales = ttk.LabelFrame(main_frame, text="Totales", padding="10")
        frame_totales.pack(fill=tk.X, pady=(0, 10))
        
        # IRPF
        frame_irpf = ttk.Frame(frame_totales)
        frame_irpf.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_irpf, text="Retención IRPF (%):").pack(side=tk.LEFT, padx=5)
        self.entry_irpf = ttk.Entry(frame_irpf, width=5)
        self.entry_irpf.insert(0, str(self.config_manager.config.get("irpf_por_defecto", 0)))
        self.entry_irpf.pack(side=tk.LEFT, padx=5)
        self.entry_irpf.bind('<KeyRelease>', lambda e: self.actualizar_totales())
        
        ttk.Label(frame_irpf, text="(Ej: 15% para profesionales)", 
                  font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=10)
        
        # Totales
        frame_valores = ttk.Frame(frame_totales)
        frame_valores.pack(fill=tk.X)
        
        self.label_base = ttk.Label(frame_valores, text="Base Imponible: 0.00 €", style='Subtitle.TLabel')
        self.label_base.pack(side=tk.LEFT, padx=15)
        
        self.label_iva = ttk.Label(frame_valores, text="IVA: 0.00 €", style='Subtitle.TLabel')
        self.label_iva.pack(side=tk.LEFT, padx=15)
        
        self.label_irpf = ttk.Label(frame_valores, text="IRPF: 0.00 €", style='Subtitle.TLabel')
        self.label_irpf.pack(side=tk.LEFT, padx=15)
        
        self.label_total = ttk.Label(frame_valores, text="TOTAL: 0.00 €", style='Total.TLabel')
        self.label_total.pack(side=tk.RIGHT, padx=15)
        
        # === Opciones adicionales ===
        frame_opciones = ttk.Frame(main_frame)
        frame_opciones.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_opciones, text="Método de pago:").pack(side=tk.LEFT, padx=5)
        self.combo_pago = ttk.Combobox(frame_opciones, width=25, 
                                        values=['Transferencia bancaria', 'Efectivo', 'Tarjeta', 
                                               'PayPal', 'Domiciliación bancaria', 'Otro'])
        self.combo_pago.set('Transferencia bancaria')
        self.combo_pago.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(frame_opciones, text="Validez (días):").pack(side=tk.LEFT, padx=15)
        self.entry_validez = ttk.Entry(frame_opciones, width=5)
        self.entry_validez.insert(0, "30")
        self.entry_validez.pack(side=tk.LEFT, padx=5)
        
        # Notas
        frame_notas = ttk.Frame(main_frame)
        frame_notas.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_notas, text="Notas:").pack(side=tk.LEFT, padx=5)
        self.entry_notas = ttk.Entry(frame_notas, width=80)
        self.entry_notas.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # === Botones principales ===
        frame_generar = ttk.Frame(main_frame)
        frame_generar.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_generar, text="💾 GUARDAR Y GENERAR PDF", 
                   command=self.guardar_y_generar, style='Accent.TButton').pack(pady=10)
    
    def abrir_configuracion(self):
        """Abre la ventana de configuración"""
        VentanaConfiguracion(self, self.config_manager)
    
    def abrir_historial(self, tipo=None):
        """Abre el historial de documentos"""
        VentanaHistorial(self, self.db, tipo)
    
    def ver_pendientes_facturar(self):
        """Muestra los documentos pendientes de facturar"""
        docs = self.db.obtener_documentos_pendientes_facturar()
        if not docs:
            messagebox.showinfo("Info", "No hay documentos pendientes de facturar")
            return
        self.abrir_historial()
    
    def seleccionar_cliente(self):
        """Abre la ventana para seleccionar un cliente"""
        ventana = VentanaSeleccionarCliente(self, self.db)
        self.wait_window(ventana)
        
        if ventana.cliente_seleccionado:
            cliente = ventana.cliente_seleccionado
            self.cliente_entries['nombre'].delete(0, tk.END)
            self.cliente_entries['nombre'].insert(0, cliente['nombre'])
            self.cliente_entries['nif'].delete(0, tk.END)
            self.cliente_entries['nif'].insert(0, cliente['nif'])
            self.cliente_entries['direccion'].delete(0, tk.END)
            self.cliente_entries['direccion'].insert(0, cliente.get('direccion', ''))
            self.cliente_entries['codigo_postal'].delete(0, tk.END)
            self.cliente_entries['codigo_postal'].insert(0, cliente.get('codigo_postal', ''))
            self.cliente_entries['ciudad'].delete(0, tk.END)
            self.cliente_entries['ciudad'].insert(0, cliente.get('ciudad', ''))
            self.cliente_entries['provincia'].delete(0, tk.END)
            self.cliente_entries['provincia'].insert(0, cliente.get('provincia', ''))
    
    def cargar_documento_para_nuevo(self, doc_origen, nuevo_tipo):
        """Carga un documento existente para crear uno nuevo"""
        # Limpiar
        self.nuevo_documento()
        
        # Establecer tipo
        self.tipo_documento.set(nuevo_tipo)
        
        # Cargar datos del cliente
        self.cliente_entries['nombre'].insert(0, doc_origen['cliente_nombre'])
        self.cliente_entries['nif'].insert(0, doc_origen['cliente_nif'])
        self.cliente_entries['direccion'].insert(0, doc_origen.get('cliente_direccion', ''))
        self.cliente_entries['codigo_postal'].insert(0, doc_origen.get('cliente_cp', ''))
        self.cliente_entries['ciudad'].insert(0, doc_origen.get('cliente_ciudad', ''))
        self.cliente_entries['provincia'].insert(0, doc_origen.get('cliente_provincia', ''))
        
        # Cargar items
        for item in doc_origen['items']:
            self.items.append({
                'descripcion': item['descripcion'],
                'cantidad': item['cantidad'],
                'unidad': item.get('unidad', 'unidad'),
                'precio_unitario': item['precio_unitario'],
                'iva': item['iva_porcentaje'],
                'subtotal': item['subtotal']
            })
            
            self.tree_items.insert('', tk.END, values=(
                item['descripcion'],
                f"{item['cantidad']:.2f}",
                item.get('unidad', 'unidad'),
                f"{item['precio_unitario']:.2f} €",
                f"{item['iva_porcentaje']}%",
                f"{item['subtotal']:.2f} €"
            ))
        
        # Cargar IRPF
        self.entry_irpf.delete(0, tk.END)
        self.entry_irpf.insert(0, str(int(doc_origen.get('irpf_porcentaje', 0))))
        
        # Guardar referencia al documento origen
        self.documento_origen_id = doc_origen['id']
        self.documento_origen_numero = doc_origen['numero']
        
        self.actualizar_totales()
        
        messagebox.showinfo("Info", 
            f"Datos cargados desde {doc_origen['tipo']} {doc_origen['numero']}.\n"
            f"Revisa y genera el nuevo {nuevo_tipo}.")
    
    def añadir_item(self):
        """Añade un item al documento"""
        descripcion = self.entry_descripcion.get().strip()
        if not descripcion:
            messagebox.showwarning("Aviso", "Introduce una descripción")
            return
        
        try:
            cantidad = float(self.entry_cantidad.get().replace(',', '.'))
            precio = float(self.entry_precio.get().replace(',', '.'))
            iva = int(self.combo_iva.get())
        except ValueError:
            messagebox.showerror("Error", "Cantidad y precio deben ser números válidos")
            return
        
        unidad = self.combo_unidad.get() or 'unidad'
        subtotal = cantidad * precio
        
        item = {
            'descripcion': descripcion,
            'cantidad': cantidad,
            'unidad': unidad,
            'precio_unitario': precio,
            'iva': iva,
            'subtotal': subtotal
        }
        
        self.items.append(item)
        
        self.tree_items.insert('', tk.END, values=(
            descripcion,
            f"{cantidad:.2f}",
            unidad,
            f"{precio:.2f} €",
            f"{iva}%",
            f"{subtotal:.2f} €"
        ))
        
        # Limpiar campos
        self.entry_descripcion.delete(0, tk.END)
        self.entry_cantidad.delete(0, tk.END)
        self.entry_cantidad.insert(0, "1")
        self.entry_precio.delete(0, tk.END)
        
        self.actualizar_totales()
    
    def eliminar_item(self):
        """Elimina el item seleccionado"""
        seleccion = self.tree_items.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona un item para eliminar")
            return
        
        index = self.tree_items.index(seleccion[0])
        del self.items[index]
        self.tree_items.delete(seleccion[0])
        self.actualizar_totales()
    
    def actualizar_totales(self):
        """Actualiza los totales del documento"""
        base_imponible = sum(item['subtotal'] for item in self.items)
        total_iva = sum(item['subtotal'] * item['iva'] / 100 for item in self.items)
        
        try:
            irpf_porcentaje = float(self.entry_irpf.get().replace(',', '.'))
        except ValueError:
            irpf_porcentaje = 0
        
        total_irpf = base_imponible * irpf_porcentaje / 100
        total = base_imponible + total_iva - total_irpf
        
        self.label_base.config(text=f"Base Imponible: {base_imponible:.2f} €")
        self.label_iva.config(text=f"IVA: {total_iva:.2f} €")
        self.label_irpf.config(text=f"IRPF: -{total_irpf:.2f} €")
        self.label_total.config(text=f"TOTAL: {total:.2f} €")
    
    def nuevo_documento(self):
        """Limpia todo para un nuevo documento"""
        for entry in self.cliente_entries.values():
            entry.delete(0, tk.END)
        
        self.items = []
        for item in self.tree_items.get_children():
            self.tree_items.delete(item)
        
        self.entry_irpf.delete(0, tk.END)
        self.entry_irpf.insert(0, str(self.config_manager.config.get("irpf_por_defecto", 0)))
        
        self.entry_notas.delete(0, tk.END)
        
        # Limpiar referencia a documento origen
        self.documento_origen_id = None
        self.documento_origen_numero = None
        
        self.actualizar_totales()
    
    def validar_datos(self):
        """Valida que todos los datos necesarios estén completos"""
        emisor = self.config_manager.config.get("emisor", {})
        if not emisor.get("nombre") or not emisor.get("nif"):
            messagebox.showerror("Error", 
                "Configura los datos del emisor primero\n(Menú Configuración > Datos del Emisor)")
            return False
        
        if not self.cliente_entries['nombre'].get().strip():
            messagebox.showerror("Error", "El nombre del cliente es obligatorio")
            return False
        if not self.cliente_entries['nif'].get().strip():
            messagebox.showerror("Error", "El NIF/CIF del cliente es obligatorio")
            return False
        
        if not self.items:
            messagebox.showerror("Error", "Añade al menos un concepto")
            return False
        
        return True
    
    def guardar_y_generar(self):
        """Guarda el documento en la base de datos y genera el PDF"""
        if not self.validar_datos():
            return
        
        tipo = self.tipo_documento.get()
        config = self.config_manager.config
        
        # Obtener serie según tipo
        series = {
            'presupuesto': config.get('serie_presupuesto', 'P'),
            'albaran': config.get('serie_albaran', 'AL'),
            'factura': config.get('serie_factura', 'A')
        }
        serie = series.get(tipo, 'A')
        
        # Generar número
        numero = self.db.generar_numero_documento(tipo, serie)
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        
        # Calcular totales
        base_imponible = sum(item['subtotal'] for item in self.items)
        total_iva = sum(item['subtotal'] * item['iva'] / 100 for item in self.items)
        
        try:
            irpf_porcentaje = float(self.entry_irpf.get().replace(',', '.'))
        except ValueError:
            irpf_porcentaje = 0
        
        total_irpf = base_imponible * irpf_porcentaje / 100
        total = base_imponible + total_iva - total_irpf
        
        # Fecha de validez para presupuestos
        fecha_validez = None
        if tipo == 'presupuesto':
            try:
                dias_validez = int(self.entry_validez.get())
                fecha_validez = (datetime.now() + timedelta(days=dias_validez)).strftime("%d/%m/%Y")
            except ValueError:
                fecha_validez = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
        
        # Guardar cliente
        cliente_data = {
            'nombre': self.cliente_entries['nombre'].get().strip(),
            'nif': self.cliente_entries['nif'].get().strip(),
            'direccion': self.cliente_entries['direccion'].get().strip(),
            'codigo_postal': self.cliente_entries['codigo_postal'].get().strip(),
            'ciudad': self.cliente_entries['ciudad'].get().strip(),
            'provincia': self.cliente_entries['provincia'].get().strip()
        }
        cliente_id = self.db.guardar_cliente(cliente_data)
        
        # Preparar datos del documento
        documento_data = {
            'tipo': tipo,
            'numero': numero,
            'fecha_emision': fecha_actual,
            'fecha_validez': fecha_validez,
            'cliente_id': cliente_id,
            'cliente_nombre': cliente_data['nombre'],
            'cliente_nif': cliente_data['nif'],
            'cliente_direccion': cliente_data['direccion'],
            'cliente_cp': cliente_data['codigo_postal'],
            'cliente_ciudad': cliente_data['ciudad'],
            'cliente_provincia': cliente_data['provincia'],
            'base_imponible': base_imponible,
            'total_iva': total_iva,
            'irpf_porcentaje': irpf_porcentaje,
            'total_irpf': total_irpf,
            'total': total,
            'metodo_pago': self.combo_pago.get(),
            'estado': 'pendiente',
            'documento_origen_id': self.documento_origen_id,
            'notas': self.entry_notas.get().strip()
        }
        
        # Guardar en base de datos
        documento_id = self.db.guardar_documento(documento_data, self.items)
        
        # Si viene de otro documento, marcar el origen como facturado
        if self.documento_origen_id:
            self.db.actualizar_estado_documento(self.documento_origen_id, 'facturado')
        
        # Desglose de IVA
        desglose_iva = {}
        for item in self.items:
            tipo_iva = item['iva']
            if tipo_iva not in desglose_iva:
                desglose_iva[tipo_iva] = {'base': 0, 'cuota': 0}
            desglose_iva[tipo_iva]['base'] += item['subtotal']
            desglose_iva[tipo_iva]['cuota'] += item['subtotal'] * tipo_iva / 100
        
        # Preparar datos para PDF
        datos_pdf = {
            'tipo': tipo,
            'numero': numero,
            'fecha_emision': fecha_actual,
            'fecha_validez': fecha_validez,
            'fecha_operacion': fecha_actual,
            'emisor': config['emisor'],
            'cliente': cliente_data,
            'items': self.items,
            'totales': {
                'base_imponible': base_imponible,
                'total_iva': total_iva,
                'irpf_porcentaje': irpf_porcentaje,
                'total_irpf': total_irpf,
                'total': total,
                'desglose_iva': desglose_iva
            },
            'metodo_pago': self.combo_pago.get(),
            'notas': self.entry_notas.get().strip()
        }
        
        if self.documento_origen_numero:
            datos_pdf['documento_origen'] = self.documento_origen_numero
        
        # Generar PDF automáticamente en carpeta organizada
        tipos_nombre = {'presupuesto': 'Presupuesto', 'albaran': 'Albarán', 'factura': 'Factura'}
        ruta = obtener_ruta_documento(tipo, numero)
        
        try:
            generador = GeneradorPDF()
            generador.generar_documento(datos_pdf, ruta)
            
            # Guardar ruta del PDF en la base de datos
            self.db.actualizar_ruta_pdf(documento_id, ruta)
            
            messagebox.showinfo("Éxito", 
                f"{tipos_nombre.get(tipo, 'Documento')} guardado correctamente.\n\n"
                f"Número: {numero}\n"
                f"PDF: {ruta}")
            
            if messagebox.askyesno("Abrir PDF", "¿Deseas abrir el PDF?"):
                os.startfile(ruta)
            
            # Limpiar para nuevo documento
            if messagebox.askyesno("Nuevo documento", "¿Crear un nuevo documento?"):
                self.nuevo_documento()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar PDF:\n{str(e)}")
    
    def salir(self):
        """Cierra la aplicación"""
        self.db.cerrar()
        self.quit()


def main():
    app = AplicacionFacturador()
    app.protocol("WM_DELETE_WINDOW", app.salir)
    app.mainloop()


if __name__ == "__main__":
    main()
