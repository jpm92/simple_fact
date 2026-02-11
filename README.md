# Facturador España 🇪🇸 v2.0

Software de facturación para autónomos y empresas en España que cumple con los requisitos legales vigentes.

## Características

- ✅ Cumple con el **Real Decreto 1619/2012** (Reglamento de Facturación)
- ✅ **Flujo completo**: Presupuesto → Albarán → Factura
- ✅ Generación de documentos en **PDF**
- ✅ **Base de datos SQLite** para guardar todo el historial
- ✅ Numeración secuencial automática por tipo de documento
- ✅ Soporte para diferentes tipos de **IVA** (0%, 4%, 10%, 21%)
- ✅ Soporte para **retención de IRPF** (para autónomos profesionales)
- ✅ **Unidades personalizables** (horas, servicios, días, unidades, etc.)
- ✅ Desglose de IVA por tipo impositivo
- ✅ Datos obligatorios según la normativa española
- ✅ Configuración persistente de datos del emisor
- ✅ **IBAN** para pagos por transferencia
- ✅ Gestión de **clientes** (se guardan automáticamente)
- ✅ **Estados de documentos**: Pendiente, Aceptado, Facturado, Pagado

## Flujo de Trabajo

```
📋 PRESUPUESTO  →  ✅ Aceptado  →  📦 ALBARÁN  →  🧾 FACTURA  →  💰 Pagado
       ↓                                              ↑
       └──────────────────────────────────────────────┘
                (También puedes facturar directamente)
```

1. **Crear Presupuesto**: Envía al cliente para su aprobación
2. **Marcar como Aceptado**: Cuando el cliente acepta
3. **Crear Albarán** (opcional): Documento de entrega
4. **Generar Factura**: Desde presupuesto o albarán
5. **Marcar como Pagado**: Cuando recibas el pago

## Datos obligatorios incluidos en la factura

Según la normativa española, una factura debe contener:

1. **Número de factura** (serie y numeración correlativa)
2. **Fecha de expedición**
3. **Nombre y apellidos o razón social del emisor**
4. **NIF del emisor**
5. **Domicilio del emisor**
6. **Nombre y apellidos o razón social del destinatario**
7. **NIF del destinatario**
8. **Descripción de las operaciones**
9. **Base imponible**
10. **Tipo impositivo aplicado**
11. **Cuota tributaria**
12. **Importe total**
13. **Retención de IRPF** (si aplica)

## Instalación

### Requisitos
- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos

1. Clona o descarga este repositorio

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecuta la aplicación:
```bash
python facturador.py
```

## Uso

### 1. Configurar datos del emisor
- Ve a **Configuración > Datos del Emisor**
- Rellena todos tus datos fiscales (nombre, NIF, dirección, etc.)
- **¡IMPORTANTE!** Añade tu **IBAN** para que aparezca en las facturas
- Configura las series de documentos (P para presupuestos, AL para albaranes, A para facturas)
- Configura el IVA por defecto (21% general)
- Configura el IRPF por defecto si eres autónomo profesional (15% o 7% nuevos autónomos)
- Guarda la configuración

### 2. Crear un documento
1. Selecciona el **tipo de documento** (Presupuesto, Albarán o Factura)
2. Rellena los **datos del cliente** (o selecciona uno existente)
3. Añade los **conceptos/items**:
   - Escribe la descripción
   - Indica la cantidad
   - Selecciona la **unidad** (horas, servicios, unidades, días...)
   - Indica el precio unitario
   - Selecciona el tipo de IVA
   - Haz clic en "Añadir Item"
4. Ajusta la **retención de IRPF** si es necesario
5. Selecciona el **método de pago**
6. Haz clic en **"GUARDAR Y GENERAR PDF"**

### 3. Gestionar el flujo Presupuesto → Factura
1. Ve a **Ver > Presupuestos**
2. Selecciona un presupuesto y haz clic en **"Marcar Aceptado"**
3. Luego puedes:
   - **"Crear Albarán"** para generar un albarán de entrega
   - **"Facturar"** para generar directamente la factura

## Retención de IRPF

## Retención de IRPF

La retención de IRPF es obligatoria cuando un autónomo profesional factura a empresas o a otros autónomos.

| Situación | Porcentaje |
|-----------|------------|
| Autónomo profesional (general) | 15% |
| Nuevos autónomos (primeros 3 años) | 7% |
| Actividades agrícolas/ganaderas | 2% |

**Nota**: Si facturas a particulares, no se aplica retención de IRPF.

## Tipos de IVA en España (2025)

| Tipo | Porcentaje | Aplicación |
|------|------------|------------|
| General | 21% | Tipo general para la mayoría de productos y servicios |
| Reducido | 10% | Alimentos, transporte, hostelería, etc. |
| Superreducido | 4% | Productos de primera necesidad, libros, medicamentos, etc. |
| Exento | 0% | Operaciones exentas (sanidad, educación, etc.) |

## Estructura de archivos

```
Facturador/
├── facturador.py      # Aplicación principal con interfaz gráfica
├── database.py        # Gestión de base de datos SQLite
├── pdf_generator.py   # Generación de PDFs
├── config.json        # Configuración del emisor
├── facturador.db      # Base de datos (se crea automáticamente)
├── requirements.txt   # Dependencias
└── README.md          # Este archivo
```

## Personalización

### Modificar las series de documentos
En la configuración puedes cambiar las series:
- `A` para facturas normales
- `P` para presupuestos
- `AL` para albaranes
- `R` para facturas rectificativas

### Numeración
El formato de numeración es: `PREFIJO-SERIE-AÑO-NUMERO`
- Presupuestos: `PP-2025-0001`
- Albaranes: `ALA-2025-0001`  
- Facturas: `A-2025-0001`

### Unidades disponibles
- `unidad` - Para productos
- `hora` - Para servicios por hora
- `servicio` - Para servicios completos
- `día` - Para trabajos por día
- `mes` - Para cuotas mensuales
- `kg` - Para productos por peso
- `m²` - Para superficies
- `proyecto` - Para proyectos completos

## Notas legales

Este software es una herramienta de ayuda para la generación de facturas. 
El usuario es responsable de:
- Verificar que los datos son correctos
- Cumplir con sus obligaciones fiscales
- Conservar las facturas según la normativa vigente (4 años)
- Declarar correctamente el IVA repercutido

## Licencia

Software libre para uso personal y comercial.

---

Desarrollado para cumplir con la normativa de facturación española vigente en 2025.
