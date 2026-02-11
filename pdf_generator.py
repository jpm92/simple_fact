"""
Generador de PDFs para el Facturador
Genera presupuestos, albaranes y facturas en formato PDF
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


class GeneradorPDF:
    """Genera documentos en formato PDF"""
    
    TITULOS = {
        'presupuesto': 'PRESUPUESTO',
        'albaran': 'ALBARÁN DE ENTREGA',
        'factura': 'FACTURA'
    }
    
    COLORES = {
        'presupuesto': colors.HexColor('#2980b9'),  # Azul
        'albaran': colors.HexColor('#27ae60'),       # Verde
        'factura': colors.HexColor('#2c3e50')        # Gris oscuro
    }
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.crear_estilos_personalizados()
    
    def crear_estilos_personalizados(self):
        """Crea estilos personalizados para el PDF"""
        self.styles.add(ParagraphStyle(
            name='TituloDocumento',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        self.styles.add(ParagraphStyle(
            name='DatosEmisor',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT
        ))
        self.styles.add(ParagraphStyle(
            name='DatosCliente',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_LEFT
        ))
        self.styles.add(ParagraphStyle(
            name='TextoLegal',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))
        self.styles.add(ParagraphStyle(
            name='NotasDocumento',
            parent=self.styles['Normal'],
            fontSize=9,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#555555')
        ))
    
    def generar_documento(self, datos, ruta_salida):
        """Genera el PDF del documento (presupuesto, albarán o factura)"""
        tipo = datos.get('tipo', 'factura')
        color_principal = self.COLORES.get(tipo, self.COLORES['factura'])
        
        doc = SimpleDocTemplate(
            ruta_salida,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        elementos = []
        
        # Título
        titulo = self.TITULOS.get(tipo, 'DOCUMENTO')
        elementos.append(Paragraph(titulo, self.styles['TituloDocumento']))
        elementos.append(Spacer(1, 10*mm))
        
        # Información del documento (número y fechas)
        info_doc = [
            [f"Nº {titulo.split()[0]}:", datos['numero']],
            ["Fecha emisión:", datos['fecha_emision']],
        ]
        
        if tipo == 'presupuesto' and datos.get('fecha_validez'):
            info_doc.append(["Válido hasta:", datos['fecha_validez']])
        elif tipo == 'factura':
            info_doc.append(["Fecha operación:", datos.get('fecha_operacion', datos['fecha_emision'])])
        
        if datos.get('documento_origen'):
            info_doc.append(["Origen:", datos['documento_origen']])
        
        tabla_info = Table(info_doc, colWidths=[45*mm, 55*mm])
        tabla_info.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('TEXTCOLOR', (0, 0), (0, -1), color_principal),
        ]))
        elementos.append(tabla_info)
        elementos.append(Spacer(1, 10*mm))
        
        # Datos emisor y cliente en paralelo
        emisor = datos['emisor']
        cliente = datos['cliente']
        
        # Construir datos del emisor con IBAN si existe
        datos_bancarios = ""
        if emisor.get('iban'):
            datos_bancarios = f"<br/>IBAN: {emisor['iban']}"
        
        datos_emisor = f"""
        <b>EMISOR</b><br/>
        <b>{emisor['nombre']}</b><br/>
        NIF/CIF: {emisor['nif']}<br/>
        {emisor['direccion']}<br/>
        {emisor['codigo_postal']} {emisor['ciudad']}<br/>
        {emisor['provincia']}<br/>
        Tel: {emisor['telefono']}<br/>
        Email: {emisor['email']}{datos_bancarios}
        """
        
        datos_cliente = f"""
        <b>CLIENTE</b><br/>
        <b>{cliente['nombre']}</b><br/>
        NIF/CIF: {cliente['nif']}<br/>
        {cliente.get('direccion', '')}<br/>
        {cliente.get('codigo_postal', '')} {cliente.get('ciudad', '')}<br/>
        {cliente.get('provincia', '')}
        """
        
        tabla_partes = Table([
            [Paragraph(datos_emisor, self.styles['DatosEmisor']),
             Paragraph(datos_cliente, self.styles['DatosCliente'])]
        ], colWidths=[85*mm, 85*mm])
        tabla_partes.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (0, 0), 0.5, colors.black),
            ('BOX', (1, 0), (1, 0), 0.5, colors.black),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla_partes)
        elementos.append(Spacer(1, 10*mm))
        
        # Tabla de conceptos/items
        encabezados = ['Descripción', 'Cantidad', 'Unidad', 'Precio Unit.', 'IVA %', 'Subtotal']
        datos_tabla = [encabezados]
        
        for item in datos['items']:
            unidad = item.get('unidad', 'unidad')
            fila = [
                item['descripcion'],
                f"{item['cantidad']:.2f}",
                unidad,
                f"{item['precio_unitario']:.2f} €",
                f"{item['iva']}%",
                f"{item['subtotal']:.2f} €"
            ]
            datos_tabla.append(fila)
        
        tabla_items = Table(datos_tabla, colWidths=[60*mm, 20*mm, 20*mm, 25*mm, 18*mm, 27*mm])
        tabla_items.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), color_principal),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')])
        ]))
        elementos.append(tabla_items)
        elementos.append(Spacer(1, 10*mm))
        
        # Totales
        totales = datos['totales']
        datos_totales = [
            ['Base Imponible:', f"{totales['base_imponible']:.2f} €"],
            ['IVA:', f"{totales['total_iva']:.2f} €"],
        ]
        
        # Añadir IRPF si aplica
        if totales.get('irpf_porcentaje', 0) > 0:
            datos_totales.append([
                f"Retención IRPF ({totales['irpf_porcentaje']}%):",
                f"-{totales['total_irpf']:.2f} €"
            ])
        
        datos_totales.append([f'TOTAL {titulo.split()[0]}:', f"{totales['total']:.2f} €"])
        
        tabla_totales = Table(datos_totales, colWidths=[50*mm, 40*mm])
        tabla_totales.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
        ]))
        
        # Alinear tabla de totales a la derecha
        tabla_totales_container = Table([[tabla_totales]], colWidths=[170*mm])
        tabla_totales_container.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]))
        elementos.append(tabla_totales_container)
        elementos.append(Spacer(1, 10*mm))
        
        # Desglose de IVA por tipo (solo para facturas)
        if tipo == 'factura' and 'desglose_iva' in totales and totales['desglose_iva']:
            elementos.append(Paragraph("<b>Desglose de IVA:</b>", self.styles['Normal']))
            elementos.append(Spacer(1, 3*mm))
            
            desglose_datos = [['Tipo IVA', 'Base Imponible', 'Cuota IVA']]
            for tipo_iva, valores in totales['desglose_iva'].items():
                desglose_datos.append([
                    f"{tipo_iva}%",
                    f"{valores['base']:.2f} €",
                    f"{valores['cuota']:.2f} €"
                ])
            
            tabla_desglose = Table(desglose_datos, colWidths=[40*mm, 50*mm, 50*mm])
            tabla_desglose.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            elementos.append(tabla_desglose)
            elementos.append(Spacer(1, 10*mm))
        
        # Método de pago y datos bancarios (para facturas)
        if tipo == 'factura' and datos.get('metodo_pago'):
            texto_pago = f"<b>Método de pago:</b> {datos['metodo_pago']}"
            if datos['metodo_pago'] == 'Transferencia bancaria' and emisor.get('iban'):
                texto_pago += f"<br/><b>IBAN:</b> {emisor['iban']}"
            elementos.append(Paragraph(texto_pago, self.styles['Normal']))
            elementos.append(Spacer(1, 5*mm))
        
        # Notas
        if datos.get('notas'):
            elementos.append(Paragraph("<b>Notas:</b>", self.styles['Normal']))
            elementos.append(Paragraph(datos['notas'], self.styles['NotasDocumento']))
            elementos.append(Spacer(1, 5*mm))
        
        # Texto específico según tipo de documento
        if tipo == 'presupuesto':
            texto_legal = f"""
            Este presupuesto tiene validez hasta la fecha indicada.
            Los precios incluyen IVA según los tipos indicados.
            Para aceptar este presupuesto, póngase en contacto con nosotros.
            """
        elif tipo == 'albaran':
            texto_legal = """
            Documento de entrega de mercancías/servicios.
            Conforme recibido: ______________________ Fecha: __________
            """
        else:
            texto_legal = """
            Factura emitida conforme al Real Decreto 1619/2012, de 30 de noviembre, 
            por el que se aprueba el Reglamento por el que se regulan las obligaciones de facturación.
            """
        
        elementos.append(Spacer(1, 15*mm))
        elementos.append(Paragraph(texto_legal, self.styles['TextoLegal']))
        
        # Generar PDF
        doc.build(elementos)
        return ruta_salida
