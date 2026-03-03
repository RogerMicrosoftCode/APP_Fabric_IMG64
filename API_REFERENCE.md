# 📚 API Reference - Funciones de Procesamiento de Imágenes

> Documentación técnica de las funciones del notebook de Fabric

---

## 🎯 Índice de Funciones

- [decode_and_validate_base64](#decode_and_validate_base64)
- [resize_and_encode_image](#resize_and_encode_image)
- [create_image_html_embed](#create_image_html_embed)
- [create_placeholder_html](#create_placeholder_html)
- [generate_content_table_row](#generate_content_table_row)

---

## Funciones Principales

### `decode_and_validate_base64`

Valida y decodifica una imagen en formato base64.

#### Firma

```python
def decode_and_validate_base64(base64_string: str) -> dict
```

#### Parámetros

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `base64_string` | `str` | String en formato base64 con o sin prefijo `data:image/...` |

#### Retorna

```python
{
    "valid": bool,           # True si la imagen es válida
    "format": str,           # Formato de imagen: "PNG", "JPEG", etc.
    "width": int,            # Ancho en píxeles
    "height": int,           # Alto en píxeles
    "size_kb": float,        # Tamaño en kilobytes
    "error": str,            # Mensaje de error (solo si valid=False)
    "html": str              # HTML placeholder (solo si valid=False)
}
```

#### Ejemplo de Uso

```python
result = decode_and_validate_base64(employee_photo_base64)

if result["valid"]:
    print(f"Imagen válida: {result['format']} - {result['width']}x{result['height']}px")
else:
    print(f"Error: {result['error']}")
```

#### Casos Especiales

- **Campo vacío**: Retorna `valid=False` con placeholder HTML
- **Base64 con prefijo**: Automáticamente remueve el prefijo `data:image/png;base64,`
- **Formato no reconocido**: Intenta decodificar de todas formas

---

### `resize_and_encode_image`

Redimensiona una imagen y la re-encodifica en base64.

#### Firma

```python
def resize_and_encode_image(
    base64_string: str, 
    max_width: int = 300, 
    max_height: int = 300
) -> str
```

#### Parámetros

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `base64_string` | `str` | - | Imagen en base64 |
| `max_width` | `int` | 300 | Ancho máximo en píxeles |
| `max_height` | `int` | 300 | Alto máximo en píxeles |

#### Retorna

```python
str  # Nueva imagen redimensionada en base64 (sin prefijo)
```

#### Comportamiento

1. **Mantiene aspect ratio**: La imagen se escala proporcionalmente
2. **Convierte a RGB**: Imágenes RGBA se convierten a RGB con fondo blanco
3. **Compresión**: Aplica `quality=85` y `optimize=True`
4. **Formato original**: Mantiene el formato de la imagen original

#### Ejemplo de Uso

```python
# Redimensionar a 200x200px
small_base64 = resize_and_encode_image(large_base64, 200, 200)

# Redimensionar con valores por defecto (300x300px)
medium_base64 = resize_and_encode_image(large_base64)
```

#### Algoritmo de Redimensionamiento

```python
# Ejemplo: Imagen original 1200x800
# max_width=300, max_height=300

# Resultado: 300x200 (mantiene aspect ratio 3:2)
```

---

### `create_image_html_embed`

Genera código HTML para embeber la imagen en el template del agente.

#### Firma

```python
def create_image_html_embed(
    base64_string: str, 
    alt_text: str = "Employee Photo", 
    employee_id: str = ""
) -> str
```

#### Parámetros

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `base64_string` | `str` | - | Imagen en base64 |
| `alt_text` | `str` | "Employee Photo" | Texto alternativo para accesibilidad |
| `employee_id` | `str` | "" | ID del empleado para caption |

#### Retorna

```python
str  # HTML completo con <div>, <img> y <p> para caption
```

#### HTML Generado

```html
<div style="text-align: center; margin: 20px 0;">
    <img src="data:image/jpeg;base64,{base64_data}" 
         alt="Employee Photo" 
         style="max-width: 300px; max-height: 300px; 
                border-radius: 8px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);" />
    <p style="font-size: 12px; color: #666; margin-top: 8px;">
        ID: 102025
    </p>
</div>
```

#### Estilos Aplicados

| Propiedad | Valor | Propósito |
|-----------|-------|-----------|
| `max-width` | 300px | Limita ancho máximo |
| `max-height` | 300px | Limita alto máximo |
| `border-radius` | 8px | Bordes redondeados |
| `box-shadow` | 0 2px 8px rgba(0,0,0,0.15) | Sombra sutil |
| `text-align` | center | Centra la imagen |

#### Ejemplo de Uso

```python
# Uso básico
html = create_image_html_embed(photo_base64)

# Con ID de empleado
html = create_image_html_embed(photo_base64, "Foto del Empleado", "102025")

# Uso en PySpark UDF
spark.udf.register("create_html_udf", create_image_html_embed, StringType())
df = df.withColumn("photo_html", F.expr("create_html_udf(PhotoBase64, 'Photo', EmployeeID)"))
```

---

### `create_placeholder_html`

Genera un placeholder visual cuando no hay foto disponible.

#### Firma

```python
def create_placeholder_html() -> str
```

#### Parámetros

Ninguno (función sin parámetros)

#### Retorna

```python
str  # HTML con ícono de usuario y gradiente
```

#### HTML Generado

```html
<div style="width: 200px; height: 200px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 8px; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            margin: 20px auto; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
    <span style="color: white; font-size: 48px; font-weight: bold;">👤</span>
</div>
```

#### Diseño Visual

```
┌─────────────────────┐
│                     │
│                     │
│        👤          │  ← Gradiente morado/azul
│                     │
│                     │
└─────────────────────┘
   200x200px circular
```

#### Ejemplo de Uso

```python
# Cuando no hay foto
if not employee_photo:
    html = create_placeholder_html()
else:
    html = create_image_html_embed(employee_photo)
```

---

### `generate_content_table_row`

Genera el texto formateado completo para una fila del `content_table`.

#### Firma

```python
def generate_content_table_row(row: Row) -> str
```

#### Parámetros

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `row` | `pyspark.sql.Row` | Fila con datos del empleado incluyendo `employee_photo_html` |

#### Campos Requeridos en el Row

```python
row.EmployeeID          # ID del empleado
row.FullName            # Nombre completo
row.JobTitle            # Puesto
row.Department          # Departamento
row.employee_photo_html # HTML de la foto (generado previamente)
row.YearsOfService      # Años en la empresa
row.Email               # Email corporativo
```

#### Retorna

```python
str  # Template completo en formato Markdown con HTML embebido
```

#### Template Generado

````markdown
**Información del Empleado ID: 102025**

---

### Fotografía
<div style="..."><img src="data:image/jpeg;base64,..."></div>

---

### Datos Personales
- **Nombre Completo:** Gerardo Silvestre Reyna Camacho
- **Posición:** Manager Data Architecture & Engineering
- **Departamento:** IT
- **ID de Empleado:** 102025

---

### Información Profesional
- **Años en la Empresa:** 7.5 años
- **Email Corporativo:** gerardo.reyna@cemex.com

---

*Generado automáticamente por OHR Agent*
````

#### Ejemplo de Uso

```python
# Como UDF de PySpark
spark.udf.register("generate_content_udf", generate_content_table_row, StringType())

df_final = df.withColumn(
    "text",
    F.expr("""
        generate_content_udf(
            struct(EmployeeID, FullName, JobTitle, Department, 
                   employee_photo_html, YearsOfService, Email)
        )
    """)
)
```

---

## 🔧 Uso en PySpark

### Registrar UDFs

```python
from pyspark.sql.types import StringType

# Registrar todas las funciones como UDFs
spark.udf.register("validate_base64_udf", decode_and_validate_base64, StringType())
spark.udf.register("create_html_embed_udf", create_image_html_embed, StringType())
spark.udf.register("generate_content_udf", generate_content_table_row, StringType())
```

### Pipeline Completo

```python
# 1. Leer datos
df = spark.table("hr_database.employees")

# 2. Generar HTML de fotos
df = df.withColumn(
    "employee_photo_html",
    F.expr("create_html_embed_udf(PhotoBase64, 'Employee Photo', EmployeeID)")
)

# 3. Generar content_table
df = df.withColumn(
    "text",
    F.expr("generate_content_udf(struct(...))")
)

# 4. Agregar metadatos
df = df.withColumn("annotations", F.lit(None).cast(StringType()))
df = df.withColumn("meta", F.to_json(F.struct(
    F.col("EmployeeID").alias("employee_id"),
    F.current_timestamp().alias("generated_at")
)))

# 5. Guardar
df.select("EmployeeID", "annotations", "meta", "text") \
  .write \
  .format("delta") \
  .mode("overwrite") \
  .saveAsTable("hr_database.ohr_agent_content_table")
```

---

## ⚠️ Manejo de Errores

### Try-Catch en Funciones

Todas las funciones incluyen manejo de errores:

```python
try:
    # Procesamiento normal
    image = decode_base64(...)
    return result
except Exception as e:
    # Fallback a placeholder
    print(f"Error: {e}")
    return create_placeholder_html()
```

### Logs de Errores

```python
# Los errores se registran automáticamente
# Ejemplo de output en caso de error:

# Error en resize: invalid base64 string
# Error creando HTML: cannot identify image file
```

---

## 📊 Performance

### Métricas de Referencia

| Operación | Tiempo Promedio | Notas |
|-----------|-----------------|-------|
| `decode_and_validate_base64` | ~50ms | Por imagen de 500KB |
| `resize_and_encode_image` | ~100ms | De 2MB a 50KB |
| `create_image_html_embed` | ~150ms | Incluye redimensionamiento |
| Pipeline completo | ~200ms | Por empleado |

### Optimización

```python
# Para datasets grandes, usa particionamiento
df.repartition(10).withColumn("photo_html", ...)

# Cache resultados intermedios
df_processed.cache()
```

---

## 🧪 Testing

### Unit Tests

```python
# Test: Validación de base64 válido
valid_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
result = decode_and_validate_base64(valid_base64)
assert result["valid"] == True
assert result["format"] == "PNG"

# Test: Base64 inválido
invalid_base64 = "invalid_string"
result = decode_and_validate_base64(invalid_base64)
assert result["valid"] == False
assert "html" in result

# Test: Redimensionamiento
resized = resize_and_encode_image(large_image, 100, 100)
decoded = decode_and_validate_base64(resized)
assert decoded["width"] <= 100
assert decoded["height"] <= 100
```

---

## 📖 Ejemplos Avanzados

### Ejemplo 1: Validación Masiva

```python
# Validar todas las imágenes de la tabla
validation_df = df.withColumn(
    "validation",
    F.expr("validate_base64_udf(PhotoBase64)")
)

# Ver estadísticas
validation_df.groupBy("validation").count().show()
```

### Ejemplo 2: Múltiples Tamaños

```python
# Generar thumbnails de diferentes tamaños
df = df.withColumn("photo_small", resize_udf(F.col("PhotoBase64"), F.lit(100), F.lit(100)))
df = df.withColumn("photo_medium", resize_udf(F.col("PhotoBase64"), F.lit(300), F.lit(300)))
df = df.withColumn("photo_large", resize_udf(F.col("PhotoBase64"), F.lit(600), F.lit(600)))
```

### Ejemplo 3: Batch Processing

```python
from pyspark.sql.window import Window

# Procesar en lotes de 1000 empleados
window = Window.partitionBy((F.col("EmployeeID") / 1000).cast("int"))

df = df.withColumn("batch_id", F.row_number().over(window))
df = df.withColumn("photo_html", F.expr("create_html_embed_udf(PhotoBase64, 'Photo', EmployeeID)"))
```

---

<div align="center">

## 🎓 Resumen

Estas funciones forman el núcleo del procesamiento de imágenes en Fabric Data Agent.

**Flujo típico:**
```
decode_and_validate_base64 → resize_and_encode_image → 
create_image_html_embed → generate_content_table_row
```

</div>
