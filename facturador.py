"""
Software de Facturación para España - Versión 3.0
Modelo basado en VENTAS: cada venta agrupa presupuesto, albarán y factura.

Cumple con los requisitos legales según la normativa española vigente
- Ley 58/2003 General Tributaria
- Real Decreto 1619/2012 (Reglamento de Facturación)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from database import Database
from pdf_generator import GeneradorPDF

# Directorio base para documentos generados
DOCUMENTOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Documentos")


def obtener_ruta_documento(tipo, numero):
    """Genera la ruta organizada para guardar un PDF.
    Estructura: Documentos/<Tipo>/<Año>/<archivo>.pdf
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


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

class ConfigManager:
    """Gestiona la configuración del emisor y facturas"""
    
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.cargar_config()
    
    def cargar_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
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
        return {
            "emisor": {
                "nombre": "", "nif": "", "direccion": "",
                "codigo_postal": "", "ciudad": "", "provincia": "",
                "email": "", "telefono": "", "iban": ""
            },
            "serie_factura": "A",
            "serie_presupuesto": "P",
            "serie_albaran": "AL",
            "iva_por_defecto": 21,
            "irpf_por_defecto": 0
        }
    
    def guardar_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)


# =============================================================================
# VENTANA DE CONFIGURACIÓN
# =============================================================================

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
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, padding="20")
        
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        ttk.Label(frame, text="Datos del Emisor (Tu empresa/autónomo)", 
                  font=('Helvetica', 12, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
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
        
        ttk.Separator(frame, orient='horizontal').grid(
            row=len(campos)+1, column=0, columnspan=2, sticky='ew', pady=15)
        
        ttk.Label(frame, text="Configuración de Series y Valores por Defecto", 
                  font=('Helvetica', 10, 'bold')).grid(
            row=len(campos)+2, column=0, columnspan=2, pady=(0, 10))
        
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
        
        ttk.Label(frame, text="(Ej: 15 para autónomos, 7 para nuevos autónomos)", 
                  font=('Segoe UI', 8)).grid(row=row_base+5, column=0, columnspan=2, sticky='w', padx=10)
        
        frame_botones = ttk.Frame(frame)
        frame_botones.grid(row=row_base+7, column=0, columnspan=2, pady=20)
        
        ttk.Button(frame_botones, text="Guardar", command=self.guardar).pack(side=tk.LEFT, padx=10)
        ttk.Button(frame_botones, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=10)
    
    def cargar_datos(self):
        emisor = self.config_manager.config.get("emisor", {})
        for campo, entry in self.entries.items():
            entry.insert(0, emisor.get(campo, ""))
        
        self.entry_serie_factura.insert(0, self.config_manager.config.get("serie_factura", "A"))
        self.entry_serie_presupuesto.insert(0, self.config_manager.config.get("serie_presupuesto", "P"))
        self.entry_serie_albaran.insert(0, self.config_manager.config.get("serie_albaran", "AL"))
        self.entry_iva.insert(0, str(self.config_manager.config.get("iva_por_defecto", 21)))
        self.entry_irpf.insert(0, str(self.config_manager.config.get("irpf_por_defecto", 0)))
    
    def guardar(self):
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


# =============================================================================
# VENTANA DE VENTAS (HISTORIAL)
# =============================================================================

class VentanaVentas(tk.Toplevel):
    """Ventana principal de gestión de ventas"""
    
    ESTADOS_DISPLAY = {
        'borrador': '📝 Borrador',
        'presupuestado': '📋 Presupuestado',
        'aceptado': '✅ Aceptado',
        'rechazado': '❌ Rechazado',
        'albaranado': '📦 Albaranado',
        'facturado': '🧾 Facturado',
        'pagado': '💰 Pagado'
    }
    
    def __init__(self, parent, db, filtro_estado=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.filtro_estado = filtro_estado
        
        self.title("Gestión de Ventas")
        self.geometry("1050x550")
        
        self.crear_widgets()
        self.cargar_datos()
        
        self.transient(parent)
    
    def crear_widgets(self):
        # === FILTROS (arriba) ===
        frame_filtros = ttk.Frame(self, padding=(10, 10, 10, 5))
        frame_filtros.pack(fill=tk.X, side=tk.TOP)
        
        ttk.Label(frame_filtros, text="Estado:").pack(side=tk.LEFT, padx=5)
        estados = ['Todos', 'Borrador', 'Presupuestado', 'Aceptado', 'Albaranado', 'Facturado', 'Pagado']
        self.combo_estado = ttk.Combobox(frame_filtros, width=15, values=estados, state='readonly')
        
        if self.filtro_estado:
            self.combo_estado.set(self.filtro_estado.capitalize())
        else:
            self.combo_estado.set('Todos')
        self.combo_estado.pack(side=tk.LEFT, padx=5)
        self.combo_estado.bind('<<ComboboxSelected>>', lambda e: self.cargar_datos())
        
        ttk.Button(frame_filtros, text="🔄 Actualizar", command=self.cargar_datos).pack(side=tk.LEFT, padx=15)
        
        # === BOTONES DE ACCIÓN (abajo) ===
        frame_inferior = ttk.Frame(self, padding=(10, 5, 10, 10))
        frame_inferior.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(frame_inferior, text="💡 Doble clic para ver detalles de la venta", 
                  font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(0, 5))
        
        frame_acciones = ttk.Frame(frame_inferior)
        frame_acciones.pack(fill=tk.X)
        
        ttk.Label(frame_acciones, text="Documentos:", 
                  font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(frame_acciones, text="📋 Presupuesto", 
                   command=lambda: self.generar_documento('presupuesto')).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acciones, text="📦 Albarán", 
                   command=lambda: self.generar_documento('albaran')).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acciones, text="🧾 Factura", 
                   command=lambda: self.generar_documento('factura')).pack(side=tk.LEFT, padx=3)
        
        ttk.Separator(frame_acciones, orient='vertical').pack(side=tk.LEFT, padx=8, fill=tk.Y)
        
        ttk.Label(frame_acciones, text="Estado:", 
                  font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 8))
        
        ttk.Button(frame_acciones, text="✅ Aceptar", 
                   command=lambda: self.cambiar_estado('aceptado')).pack(side=tk.LEFT, padx=3)
        ttk.Button(frame_acciones, text="💰 Pagado", 
                   command=lambda: self.cambiar_estado('pagado')).pack(side=tk.LEFT, padx=3)
        
        ttk.Separator(frame_acciones, orient='vertical').pack(side=tk.LEFT, padx=8, fill=tk.Y)
        
        ttk.Button(frame_acciones, text="🗑️ Eliminar", 
                   command=self.eliminar_venta).pack(side=tk.LEFT, padx=3)
        
        # === TABLA (centro) ===
        frame_tabla = ttk.Frame(self, padding=(10, 0, 10, 0))
        frame_tabla.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        columns = ('cliente', 'total', 'presupuesto', 'albaran', 'factura', 'estado', 'fecha')
        self.tree = ttk.Treeview(frame_tabla, columns=columns, show='headings', height=15)
        
        self.tree.heading('cliente', text='Cliente')
        self.tree.heading('total', text='Total')
        self.tree.heading('presupuesto', text='Presupuesto')
        self.tree.heading('albaran', text='Albarán')
        self.tree.heading('factura', text='Factura')
        self.tree.heading('estado', text='Estado')
        self.tree.heading('fecha', text='Fecha')
        
        self.tree.column('cliente', width=200)
        self.tree.column('total', width=100, anchor='e')
        self.tree.column('presupuesto', width=130, anchor='center')
        self.tree.column('albaran', width=130, anchor='center')
        self.tree.column('factura', width=130, anchor='center')
        self.tree.column('estado', width=130, anchor='center')
        self.tree.column('fecha', width=90, anchor='center')
        
        scrollbar = ttk.Scrollbar(frame_tabla, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', lambda e: self.ver_detalle_venta())
    
    def cargar_datos(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        filtro = self.combo_estado.get()
        estado = filtro.lower() if filtro != 'Todos' else None
        
        ventas = self.db.obtener_ventas(estado)
        
        for v in ventas:
            pres = v['num_presupuesto'] or '—'
            alb = v['num_albaran'] or '—'
            fact = v['num_factura'] or '—'
            
            # Marcar con ✓ si tiene el documento
            pres_display = f"✅ {pres}" if v['num_presupuesto'] else '—'
            alb_display = f"✅ {alb}" if v['num_albaran'] else '—'
            fact_display = f"✅ {fact}" if v['num_factura'] else '—'
            
            fecha = v['fecha_creacion'][:10] if v['fecha_creacion'] else ''
            
            self.tree.insert('', tk.END, iid=v['id'], values=(
                v['cliente_nombre'],
                f"{v['total']:.2f} €",
                pres_display,
                alb_display,
                fact_display,
                self.ESTADOS_DISPLAY.get(v['estado'], v['estado']),
                fecha
            ))
    
    def obtener_venta_seleccionada(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona una venta")
            return None
        return self.db.obtener_venta(int(seleccion[0]))
    
    def cambiar_estado(self, nuevo_estado):
        venta = self.obtener_venta_seleccionada()
        if not venta:
            return
        self.db.actualizar_estado_venta(venta['id'], nuevo_estado)
        self.cargar_datos()
        messagebox.showinfo("Éxito", f"Estado actualizado a: {nuevo_estado}")
    
    def generar_documento(self, tipo_doc):
        """Genera (o abre) un documento para la venta seleccionada"""
        venta = self.obtener_venta_seleccionada()
        if not venta:
            return
        
        # Si ya existe este documento, abrir el PDF
        doc_existente = venta['documentos'].get(tipo_doc)
        if doc_existente and doc_existente.get('ruta_pdf') and os.path.exists(doc_existente['ruta_pdf']):
            try:
                os.startfile(doc_existente['ruta_pdf'])
                return
            except Exception:
                pass
        
        # Validar transiciones lógicas
        if tipo_doc == 'albaran' and venta['estado'] in ('borrador',):
            if venta['documentos'].get('presupuesto'):
                # Tiene presupuesto pero no está aceptado
                if messagebox.askyesno("Confirmar", 
                        "La venta no está aceptada. ¿Marcarla como aceptada y generar albarán?"):
                    self.db.actualizar_estado_venta(venta['id'], 'aceptado')
                else:
                    return
            # Si no tiene presupuesto, se puede generar albarán directamente
        
        if tipo_doc == 'factura' and venta['estado'] in ('borrador',):
            if messagebox.askyesno("Confirmar", 
                    "La venta está en borrador. ¿Generar factura directamente?"):
                pass  # Continuar
            else:
                return
        
        # Generar número y PDF
        config = self.parent.config_manager.config
        series = {
            'presupuesto': config.get('serie_presupuesto', 'P'),
            'albaran': config.get('serie_albaran', 'AL'),
            'factura': config.get('serie_factura', 'A')
        }
        serie = series.get(tipo_doc, 'A')
        
        # Si ya tiene número (documento registrado pero sin PDF), reusar
        if doc_existente and doc_existente.get('numero'):
            numero = doc_existente['numero']
            fecha_emision = doc_existente['fecha_emision']
        else:
            numero = self.db.generar_numero_documento(tipo_doc, serie)
            fecha_emision = datetime.now().strftime("%d/%m/%Y")
        
        # Fecha validez para presupuestos
        fecha_validez = None
        if tipo_doc == 'presupuesto':
            fecha_validez = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
        
        # Preparar items
        items_pdf = []
        for item in venta['items']:
            items_pdf.append({
                'descripcion': item['descripcion'],
                'cantidad': item['cantidad'],
                'unidad': item.get('unidad', 'unidad'),
                'precio_unitario': item['precio_unitario'],
                'iva': item['iva_porcentaje'],
                'subtotal': item['subtotal']
            })
        
        # Desglose IVA
        desglose_iva = {}
        for item in items_pdf:
            tipo_iva = int(item['iva'])
            if tipo_iva not in desglose_iva:
                desglose_iva[tipo_iva] = {'base': 0, 'cuota': 0}
            desglose_iva[tipo_iva]['base'] += item['subtotal']
            desglose_iva[tipo_iva]['cuota'] += item['subtotal'] * tipo_iva / 100
        
        datos_pdf = {
            'tipo': tipo_doc,
            'numero': numero,
            'fecha_emision': fecha_emision,
            'fecha_validez': fecha_validez,
            'emisor': config['emisor'],
            'cliente': {
                'nombre': venta['cliente_nombre'],
                'nif': venta['cliente_nif'],
                'direccion': venta.get('cliente_direccion', ''),
                'codigo_postal': venta.get('cliente_cp', ''),
                'ciudad': venta.get('cliente_ciudad', ''),
                'provincia': venta.get('cliente_provincia', '')
            },
            'items': items_pdf,
            'totales': {
                'base_imponible': venta['base_imponible'],
                'total_iva': venta['total_iva'],
                'irpf_porcentaje': venta.get('irpf_porcentaje', 0),
                'total_irpf': venta.get('total_irpf', 0),
                'total': venta['total'],
                'desglose_iva': desglose_iva
            },
            'metodo_pago': venta.get('metodo_pago', ''),
            'notas': venta.get('notas', '')
        }
        
        ruta = obtener_ruta_documento(tipo_doc, numero)
        
        try:
            generador = GeneradorPDF()
            generador.generar_documento(datos_pdf, ruta)
            
            # Registrar documento en BD
            self.db.registrar_documento(
                venta['id'], tipo_doc, numero, fecha_emision, fecha_validez, ruta)
            
            # Actualizar estado de la venta
            nuevo_estado_map = {
                'presupuesto': 'presupuestado',
                'albaran': 'albaranado',
                'factura': 'facturado'
            }
            # Solo avanzar estado, no retroceder
            estados_orden = Database.ESTADOS
            estado_actual_idx = estados_orden.index(venta['estado']) if venta['estado'] in estados_orden else 0
            nuevo_estado = nuevo_estado_map.get(tipo_doc, venta['estado'])
            nuevo_estado_idx = estados_orden.index(nuevo_estado) if nuevo_estado in estados_orden else 0
            
            if nuevo_estado_idx > estado_actual_idx:
                self.db.actualizar_estado_venta(venta['id'], nuevo_estado)
            
            self.cargar_datos()
            
            tipos_nombre = {'presupuesto': 'Presupuesto', 'albaran': 'Albarán', 'factura': 'Factura'}
            messagebox.showinfo("Éxito", 
                f"{tipos_nombre[tipo_doc]} generado:\n{numero}\n\n{ruta}")
            os.startfile(ruta)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar PDF:\n{str(e)}")
    
    def eliminar_venta(self):
        venta = self.obtener_venta_seleccionada()
        if not venta:
            return
        
        # Construir info de lo que se va a borrar
        docs = []
        for tipo, nombre in [('presupuesto', 'Presupuesto'), ('albaran', 'Albarán'), ('factura', 'Factura')]:
            if tipo in venta['documentos']:
                docs.append(f"  • {nombre}: {venta['documentos'][tipo]['numero']}")
        
        docs_text = "\n".join(docs) if docs else "  (ninguno)"
        
        if not messagebox.askyesno("⚠️ Confirmar eliminación",
                f"¿Eliminar esta venta y todos sus documentos?\n\n"
                f"Cliente: {venta['cliente_nombre']}\n"
                f"Total: {venta['total']:.2f} €\n\n"
                f"Documentos que se eliminarán:\n{docs_text}\n\n"
                f"Esta acción no se puede deshacer."):
            return
        
        self.db.eliminar_venta(venta['id'])
        self.cargar_datos()
        messagebox.showinfo("Eliminado", "Venta y documentos eliminados correctamente")
    
    def ver_detalle_venta(self):
        """Muestra detalle de la venta seleccionada"""
        venta = self.obtener_venta_seleccionada()
        if not venta:
            return
        
        docs_info = []
        for tipo, nombre in [('presupuesto', 'Presupuesto'), ('albaran', 'Albarán'), ('factura', 'Factura')]:
            doc = venta['documentos'].get(tipo)
            if doc:
                tiene_pdf = "✅ PDF" if doc.get('ruta_pdf') and os.path.exists(doc['ruta_pdf']) else "⚠️ Sin PDF"
                docs_info.append(f"  {nombre}: {doc['numero']} ({tiene_pdf})")
            else:
                docs_info.append(f"  {nombre}: — (no generado)")
        
        items_info = []
        for item in venta['items']:
            items_info.append(
                f"  • {item['descripcion']}  "
                f"{item['cantidad']} {item.get('unidad', 'ud')} × {item['precio_unitario']:.2f}€ "
                f"= {item['subtotal']:.2f}€ (+{int(item['iva_porcentaje'])}% IVA)")
        
        detalle = (
            f"VENTA #{venta['id']}\n"
            f"{'='*40}\n\n"
            f"Cliente: {venta['cliente_nombre']} ({venta['cliente_nif']})\n"
            f"Estado: {self.ESTADOS_DISPLAY.get(venta['estado'], venta['estado'])}\n\n"
            f"Conceptos:\n" + "\n".join(items_info) + "\n\n"
            f"Base imponible: {venta['base_imponible']:.2f} €\n"
            f"IVA: {venta['total_iva']:.2f} €\n"
        )
        
        if venta.get('irpf_porcentaje', 0) > 0:
            detalle += f"IRPF (-{venta['irpf_porcentaje']:.0f}%): -{venta.get('total_irpf', 0):.2f} €\n"
        
        detalle += (
            f"TOTAL: {venta['total']:.2f} €\n\n"
            f"Documentos:\n" + "\n".join(docs_info)
        )
        
        messagebox.showinfo(f"Detalle de Venta #{venta['id']}", detalle)


# =============================================================================
# VENTANA SELECCIONAR CLIENTE
# =============================================================================

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
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        frame_busqueda = ttk.Frame(frame)
        frame_busqueda.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_busqueda, text="Buscar:").pack(side=tk.LEFT, padx=5)
        self.entry_busqueda = ttk.Entry(frame_busqueda, width=30)
        self.entry_busqueda.pack(side=tk.LEFT, padx=5)
        self.entry_busqueda.bind('<KeyRelease>', lambda e: self.filtrar_clientes())
        
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
        
        frame_botones = ttk.Frame(frame)
        frame_botones.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_botones, text="Seleccionar", command=self.seleccionar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botones, text="Cancelar", command=self.destroy).pack(side=tk.LEFT, padx=5)
    
    def cargar_clientes(self):
        self.clientes = self.db.obtener_clientes()
        self.mostrar_clientes(self.clientes)
    
    def mostrar_clientes(self, clientes):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for cliente in clientes:
            self.tree.insert('', tk.END, iid=cliente['id'], values=(
                cliente['nombre'], cliente['nif'], cliente.get('ciudad', '')))
    
    def filtrar_clientes(self):
        texto = self.entry_busqueda.get().lower()
        filtrados = [c for c in self.clientes if 
                     texto in c['nombre'].lower() or texto in c['nif'].lower()]
        self.mostrar_clientes(filtrados)
    
    def seleccionar(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona un cliente")
            return
        self.cliente_seleccionado = self.db.obtener_cliente(int(seleccion[0]))
        self.destroy()


# =============================================================================
# APLICACIÓN PRINCIPAL
# =============================================================================

class AplicacionFacturador(tk.Tk):
    """Aplicación principal de facturación"""
    
    UNIDADES = ['unidad', 'hora', 'servicio', 'día', 'mes', 'kg', 'm²', 'proyecto']
    TEMAS_PREFERIDOS = ['vista', 'winnative', 'clam', 'alt', 'default']
    
    def __init__(self):
        super().__init__()
        
        self.aplicar_tema_nativo()
        
        self.title("Facturador España v3.0")
        self.geometry("1000x800")
        
        self.configurar_estilos()
        
        self.config_manager = ConfigManager()
        self.db = Database()
        
        # Items del documento actual
        self.items = []
        
        self.crear_menu()
        self.crear_widgets()
    
    def aplicar_tema_nativo(self):
        style = ttk.Style()
        temas_disponibles = style.theme_names()
        for tema in self.TEMAS_PREFERIDOS:
            if tema in temas_disponibles:
                try:
                    style.theme_use(tema)
                    return
                except Exception:
                    continue
    
    def configurar_estilos(self):
        style = ttk.Style()
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10), padding=6)
        style.configure('TEntry', font=('Segoe UI', 10), padding=4)
        style.configure('TCombobox', font=('Segoe UI', 10))
        style.configure('TRadiobutton', font=('Segoe UI', 10))
        style.configure('TLabelframe', font=('Segoe UI', 10, 'bold'))
        style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'))
        style.configure('Treeview', font=('Segoe UI', 10), rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        style.configure('Accent.TButton', font=('Segoe UI', 11, 'bold'), padding=10)
        style.configure('Title.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Subtitle.TLabel', font=('Segoe UI', 11))
        style.configure('Total.TLabel', font=('Segoe UI', 13, 'bold'))
    
    def crear_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Menú Archivo
        menu_archivo = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=menu_archivo)
        menu_archivo.add_command(label="Nueva Venta", command=self.nuevo_documento)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Salir", command=self.salir)
        
        # Menú Ventas
        menu_ventas = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ventas", menu=menu_ventas)
        menu_ventas.add_command(label="📋 Todas las ventas", command=lambda: self.abrir_ventas())
        menu_ventas.add_separator()
        menu_ventas.add_command(label="📝 Borradores", command=lambda: self.abrir_ventas('borrador'))
        menu_ventas.add_command(label="📋 Presupuestadas", command=lambda: self.abrir_ventas('presupuestado'))
        menu_ventas.add_command(label="✅ Aceptadas", command=lambda: self.abrir_ventas('aceptado'))
        menu_ventas.add_command(label="📦 Albaranadas", command=lambda: self.abrir_ventas('albaranado'))
        menu_ventas.add_command(label="🧾 Facturadas", command=lambda: self.abrir_ventas('facturado'))
        menu_ventas.add_command(label="💰 Pagadas", command=lambda: self.abrir_ventas('pagado'))
        
        # Menú Configuración
        menu_config = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=menu_config)
        menu_config.add_command(label="Datos del Emisor", command=self.abrir_configuracion)
    
    def crear_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === Sección Cliente ===
        frame_cliente = ttk.LabelFrame(main_frame, text="Datos del Cliente", padding="10")
        frame_cliente.pack(fill=tk.X, pady=(0, 10))
        
        frame_cliente_acciones = ttk.Frame(frame_cliente)
        frame_cliente_acciones.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(frame_cliente_acciones, text="📂 Seleccionar Cliente Existente", 
                   command=self.seleccionar_cliente).pack(side=tk.LEFT)
        
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
        
        frame_acciones_items = ttk.Frame(main_frame)
        frame_acciones_items.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(frame_acciones_items, text="🗑️ Eliminar Item Seleccionado", 
                   command=self.eliminar_item).pack(side=tk.LEFT)
        
        # === Sección IRPF y Totales ===
        frame_totales = ttk.LabelFrame(main_frame, text="Totales", padding="10")
        frame_totales.pack(fill=tk.X, pady=(0, 10))
        
        frame_irpf = ttk.Frame(frame_totales)
        frame_irpf.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_irpf, text="Retención IRPF (%):").pack(side=tk.LEFT, padx=5)
        self.entry_irpf = ttk.Entry(frame_irpf, width=5)
        self.entry_irpf.insert(0, str(self.config_manager.config.get("irpf_por_defecto", 0)))
        self.entry_irpf.pack(side=tk.LEFT, padx=5)
        self.entry_irpf.bind('<KeyRelease>', lambda e: self.actualizar_totales())
        
        ttk.Label(frame_irpf, text="(Ej: 15% para profesionales)", 
                  font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=10)
        
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
        
        # Notas
        frame_notas = ttk.Frame(main_frame)
        frame_notas.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(frame_notas, text="Notas:").pack(side=tk.LEFT, padx=5)
        self.entry_notas = ttk.Entry(frame_notas, width=80)
        self.entry_notas.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # === Botón principal ===
        frame_generar = ttk.Frame(main_frame)
        frame_generar.pack(fill=tk.X, pady=10)
        
        ttk.Button(frame_generar, text="💾 CREAR VENTA", 
                   command=self.guardar_venta, style='Accent.TButton').pack(pady=10)
    
    # === ACCIONES ===
    
    def abrir_configuracion(self):
        VentanaConfiguracion(self, self.config_manager)
    
    def abrir_ventas(self, estado=None):
        VentanaVentas(self, self.db, estado)
    
    def seleccionar_cliente(self):
        ventana = VentanaSeleccionarCliente(self, self.db)
        self.wait_window(ventana)
        
        if ventana.cliente_seleccionado:
            cliente = ventana.cliente_seleccionado
            for campo in ['nombre', 'nif', 'direccion', 'codigo_postal', 'ciudad', 'provincia']:
                self.cliente_entries[campo].delete(0, tk.END)
                self.cliente_entries[campo].insert(0, cliente.get(campo, ''))
    
    def añadir_item(self):
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
        
        self.items.append({
            'descripcion': descripcion, 'cantidad': cantidad, 'unidad': unidad,
            'precio_unitario': precio, 'iva': iva, 'subtotal': subtotal
        })
        
        self.tree_items.insert('', tk.END, values=(
            descripcion, f"{cantidad:.2f}", unidad,
            f"{precio:.2f} €", f"{iva}%", f"{subtotal:.2f} €"))
        
        self.entry_descripcion.delete(0, tk.END)
        self.entry_cantidad.delete(0, tk.END)
        self.entry_cantidad.insert(0, "1")
        self.entry_precio.delete(0, tk.END)
        
        self.actualizar_totales()
    
    def eliminar_item(self):
        seleccion = self.tree_items.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona un item para eliminar")
            return
        index = self.tree_items.index(seleccion[0])
        del self.items[index]
        self.tree_items.delete(seleccion[0])
        self.actualizar_totales()
    
    def actualizar_totales(self):
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
        for entry in self.cliente_entries.values():
            entry.delete(0, tk.END)
        self.items = []
        for item in self.tree_items.get_children():
            self.tree_items.delete(item)
        self.entry_irpf.delete(0, tk.END)
        self.entry_irpf.insert(0, str(self.config_manager.config.get("irpf_por_defecto", 0)))
        self.entry_notas.delete(0, tk.END)
        self.actualizar_totales()
    
    def validar_datos(self):
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
    
    def guardar_venta(self):
        """Crea una nueva venta en la base de datos"""
        if not self.validar_datos():
            return
        
        config = self.config_manager.config
        
        # Calcular totales
        base_imponible = sum(item['subtotal'] for item in self.items)
        total_iva = sum(item['subtotal'] * item['iva'] / 100 for item in self.items)
        
        try:
            irpf_porcentaje = float(self.entry_irpf.get().replace(',', '.'))
        except ValueError:
            irpf_porcentaje = 0
        
        total_irpf = base_imponible * irpf_porcentaje / 100
        total = base_imponible + total_iva - total_irpf
        
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
        
        # Crear venta
        venta_data = {
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
            'notas': self.entry_notas.get().strip(),
            'estado': 'borrador'
        }
        
        venta_id = self.db.crear_venta(venta_data, self.items)
        
        messagebox.showinfo("Éxito", 
            f"Venta #{venta_id} creada correctamente.\n\n"
            f"Cliente: {cliente_data['nombre']}\n"
            f"Total: {total:.2f} €\n\n"
            "Ve a Ventas para generar presupuesto, albarán o factura.")
        
        # Preguntar qué hacer
        if messagebox.askyesno("Generar documento", 
                "¿Quieres abrir la ventana de ventas para generar un documento?"):
            self.abrir_ventas()
        
        if messagebox.askyesno("Nueva venta", "¿Crear una nueva venta?"):
            self.nuevo_documento()
    
    def salir(self):
        self.db.cerrar()
        self.quit()


def main():
    app = AplicacionFacturador()
    app.protocol("WM_DELETE_WINDOW", app.salir)
    app.mainloop()


if __name__ == "__main__":
    main()
