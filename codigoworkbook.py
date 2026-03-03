# ========================================================
# NOTEBOOK COMPLETO - FABRIC DATA AGENT IMAGE PROCESSING
# ========================================================
# Copia cada sección (CELDA) en una celda separada del notebook
# Ejecuta las celdas en orden (1 → 2 → 3 → 4 → 5 → 6 → 7)

# ========================================================
# CELDA 1: Instalar Dependencias
# ========================================================
%pip install Pillow==10.2.0


# ========================================================
# CELDA 2: Importar Bibliotecas
# ========================================================
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
import base64
import io
from PIL import Image


# ========================================================
# CELDA 3: Funciones de Procesamiento (LA MÁS IMPORTANTE)
# ========================================================
def resize_and_encode_image(base64_string, max_width=300, max_height=300):
    """Redimensiona y re-codifica imagen"""
    try:
        if not base64_string or base64_string.strip() == '':
            return None
        
        # Limpiar base64
        clean_base64 = base64_string.split(',')[1] if ',' in base64_string else base64_string
        
        # Decodificar
        image_data = base64.b64decode(clean_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Redimensionar
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convertir a RGB si es necesario
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            if image.mode in ('RGBA', 'LA'):
                background.paste(image, mask=image.split()[-1])
            image = background
        
        # Re-encodificar
        buffered = io.BytesIO()
        image.save(buffered, format='JPEG', quality=85, optimize=True)
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    except:
        return None

def create_image_html(base64_string, employee_id=''):
    """Crea HTML para el template"""
    if not base64_string:
        # Placeholder si no hay imagen
        return '''<div style="width:200px;height:200px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                  border-radius:8px;display:flex;align-items:center;justify-content:center;margin:20px auto;">
                  <span style="color:white;font-size:48px;">👤</span></div>'''
    
    try:
        # Redimensionar
        resized = resize_and_encode_image(base64_string)
        if not resized:
            return create_image_html(None, employee_id)
        
        # Crear HTML
        html = f'''<div style="text-align:center;margin:20px 0;">
            <img src="data:image/jpeg;base64,{resized}" 
                 alt="Employee Photo" 
                 style="max-width:300px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.15);" />
            <p style="font-size:12px;color:#666;margin-top:8px;">ID: {employee_id}</p>
        </div>'''
        return html
    except:
        return create_image_html(None, employee_id)

# Registrar como UDF de Spark
spark.udf.register('create_html_udf', create_image_html, StringType())

print('✅ Funciones registradas correctamente')


# ========================================================
# CELDA 4: Leer Tabla de Empleados
# ========================================================
# 🔧 AJUSTA el nombre de tu tabla aquí:
tabla_empleados = 'TU_SCHEMA.TU_TABLA'  # Ejemplo: 'hr_database.employees'

df_employees = spark.table(tabla_empleados)

# Ver primeros registros
display(df_employees.limit(5))

print(f'Total de empleados: {df_employees.count()}')


# ========================================================
# CELDA 5: Procesar Imágenes
# ========================================================
# 🔧 AJUSTA el nombre del campo de foto si es diferente
campo_foto = 'PhotoBase64'  # Tu campo con base64
campo_id = 'EmployeeID'     # Tu campo de ID

df_processed = df_employees.withColumn(
    'employee_photo_html',
    F.expr(f"create_html_udf({campo_foto}, {campo_id})")
)

# Ver resultados
display(df_processed.select(
    campo_id, 
    'FullName', 
    'employee_photo_html'
).limit(3))

print('✅ Imágenes procesadas')


# ========================================================
# CELDA 6: Generar Content Table
# ========================================================
def generate_text_template(row):
    """Genera el texto formateado para el agente"""
    return f'''**Información del Empleado ID: {row.EmployeeID}**

---

### Fotografía
{row.employee_photo_html}

---

### Datos Personales
- **Nombre Completo:** {row.FullName}
- **Posición:** {row.JobTitle}
- **Departamento:** {row.Department}

---

### Información de Contacto
- **Email:** {row.Email}
- **ID:** {row.EmployeeID}

---

*Generado automáticamente por OHR Agent*
'''

# Registrar UDF
spark.udf.register('generate_text', generate_text_template, StringType())

# Aplicar template
df_content = df_processed.withColumn(
    'text',
    F.expr('''generate_text(
        struct(EmployeeID, FullName, JobTitle, 
               Department, Email, employee_photo_html)
    )''')
)

# Agregar columnas requeridas
df_content = df_content.withColumn('annotations', F.lit(None).cast(StringType()))
df_content = df_content.withColumn('meta', 
    F.to_json(F.struct(
        F.col('EmployeeID').alias('employee_id'),
        F.current_timestamp().alias('generated_at')
    ))
)

# Seleccionar solo columnas necesarias
df_final = df_content.select('EmployeeID', 'annotations', 'meta', 'text')

display(df_final.limit(2))
print('✅ Content table generado')


# ========================================================
# CELDA 7: Guardar Tabla Física
# ========================================================
# 🔧 AJUSTA el nombre de la tabla de salida
tabla_salida = 'hr_database.ohr_agent_content_table'

df_final.write \
    .format('delta') \
    .mode('overwrite') \
    .option('overwriteSchema', 'true') \
    .saveAsTable(tabla_salida)

print(f'✅ Tabla guardada: {tabla_salida}')
print(f'📊 Total registros: {df_final.count()}')


# ========================================================
# CELDA 8 (OPCIONAL): Validar Resultados
# ========================================================
# Ver la tabla guardada
result_table = spark.table(tabla_salida)
display(result_table.limit(5))

# Estadísticas
print(f'''
📊 ESTADÍSTICAS:
- Total registros: {result_table.count()}
- Columnas: {', '.join(result_table.columns)}
''')


# ========================================================
# CELDA 9 (OPCIONAL): Verificar Imágenes Procesadas
# ========================================================
# Contar imágenes válidas vs placeholders
from pyspark.sql.functions import when, col

validation = df_processed.select(
    when(col('employee_photo_html').contains('👤'), 'Sin Foto (Placeholder)')
    .otherwise('Con Foto')
    .alias('status')
).groupBy('status').count()

display(validation)

print('✅ Validación completa')


# ========================================================
# FIN DEL NOTEBOOK
# ========================================================
# Ahora ve a Fabric Data Agent y configura:
# 1. Edit Configuration
# 2. Content Protocol → Content Table
# 3. Selecciona: hr_database.ohr_agent_content_table
# 4. Mapea: annotations → annotations, meta → meta, text → text
# 5. Save
# 6. Prueba: "Dame información del empleado 102025"
# ========================================================
