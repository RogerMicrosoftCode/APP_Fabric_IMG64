# ============================================================================
# CELDA 1: INSTALAR PILLOW
# Copiar y pegar esta celda completa, luego ejecutar
# ============================================================================

%pip install Pillow==10.2.0


# ============================================================================
# CELDA 2: IMPORTS
# Copiar y pegar esta celda completa, luego ejecutar
# ============================================================================

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructType, StructField, IntegerType
import base64
import io
from PIL import Image
import json


# ============================================================================
# CELDA 3: FUNCIONES DE PROCESAMIENTO
# Copiar y pegar esta celda completa, luego ejecutar
# ============================================================================

def decode_and_validate_base64(base64_string):
    """
    Valida y decodifica imagen base64
    Retorna dict con estado y datos
    """
    try:
        if not base64_string or base64_string.strip() == "":
            return None
        
        # Limpiar el base64
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decodificar
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        
        return True
    except Exception as e:
        return None

def resize_and_encode_image(base64_string, max_width=300, max_height=300):
    """
    Redimensiona imagen y retorna nuevo base64
    """
    try:
        if not base64_string or base64_string.strip() == "":
            return None
            
        # Limpiar base64
        clean_base64 = base64_string.split(',')[1] if ',' in base64_string else base64_string
        
        # Decodificar
        image_data = base64.b64decode(clean_base64)
        image = Image.open(io.BytesIO(image_data))
        
        # Redimensionar manteniendo aspect ratio
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convertir a RGB si es necesario (para JPEG)
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
    except Exception as e:
        print(f"Error en resize: {e}")
        return None

def create_placeholder_html():
    """
    Crea placeholder cuando no hay foto disponible
    """
    return '''<div style="width: 200px; height: 200px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; margin: 20px auto; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
    <span style="color: white; font-size: 48px; font-weight: bold;">👤</span>
</div>'''

def create_image_html_embed(base64_string, alt_text="Employee Photo", employee_id=""):
    """
    Crea HTML para embeber en el template
    """
    try:
        if not base64_string or base64_string.strip() == "":
            return create_placeholder_html()
        
        # Redimensionar
        resized_base64 = resize_and_encode_image(base64_string)
        
        if not resized_base64:
            return create_placeholder_html()
        
        # Crear HTML
        html = f'''<div style="text-align: center; margin: 20px 0;">
    <img src="data:image/jpeg;base64,{resized_base64}" 
         alt="{alt_text}" 
         style="max-width: 300px; max-height: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);" />
    <p style="font-size: 12px; color: #666; margin-top: 8px;">ID: {employee_id}</p>
</div>'''
        
        return html
    except Exception as e:
        print(f"Error creando HTML: {e}")
        return create_placeholder_html()

# Registrar UDF para PySpark
spark.udf.register("create_html_embed_udf", create_image_html_embed, StringType())

print("✅ Funciones registradas correctamente")


# ============================================================================
# CELDA 4: LEER TABLA DE EMPLEADOS
# 🔧 AJUSTA el nombre de tu tabla aquí antes de ejecutar
# ============================================================================

# 🔧 CAMBIAR ESTE NOMBRE POR TU TABLA REAL
tabla_empleados = 'hr_database.employees'  # Ejemplo: 'cemex_hr.employee_data'

# Leer la tabla
df_employees = spark.table(tabla_empleados)

# Ver primeros registros
display(df_employees.limit(5))

print(f"✅ Total de empleados: {df_employees.count()}")


# ============================================================================
# CELDA 5: PROCESAR IMÁGENES Y GENERAR HTML
# 🔧 AJUSTA los nombres de campos si son diferentes
# ============================================================================

# 🔧 AJUSTAR estos nombres según tus campos
campo_foto = 'PhotoBase64'      # Campo con base64
campo_id = 'EmployeeID'         # Campo con ID del empleado

# Procesar imágenes
df_processed = df_employees.withColumn(
    "employee_photo_html",
    F.expr(f"create_html_embed_udf({campo_foto}, 'Employee Photo', {campo_id})")
)

# Ver resultados
display(df_processed.select(
    campo_id,
    'FullName',
    'employee_photo_html'
).limit(3))

print("✅ Imágenes procesadas correctamente")


# ============================================================================
# CELDA 6: GENERAR CONTENT TABLE PARA EL AGENTE
# Esta celda crea el formato exacto que necesita Fabric Data Agent
# ============================================================================

def generate_content_table_text(employee_id, full_name, job_title, department, email, photo_html, years_service):
    """
    Genera el texto formateado para el agente
    """
    template = f"""**Información del Empleado ID: {employee_id}**

---

### Fotografía
{photo_html}

---

### Datos Personales
- **Nombre Completo:** {full_name}
- **Posición:** {job_title}
- **Departamento:** {department}
- **ID de Empleado:** {employee_id}

---

### Información Profesional
- **Años en la Empresa:** {years_service} años
- **Email Corporativo:** {email}

---

*Generado automáticamente por OHR Agent*
"""
    return template

# Registrar UDF
from pyspark.sql.types import StringType
spark.udf.register("generate_text_udf", generate_content_table_text, StringType())

# Generar columna 'text' con el template completo
df_content = df_processed.withColumn(
    "text",
    F.expr("""
        generate_text_udf(
            EmployeeID,
            FullName,
            JobTitle,
            Department,
            Email,
            employee_photo_html,
            CAST(YearsOfService AS STRING)
        )
    """)
)

# Agregar columnas requeridas por Content Protocol
df_content = df_content.withColumn("annotations", F.lit(None).cast(StringType()))

df_content = df_content.withColumn("meta", 
    F.to_json(F.struct(
        F.col("EmployeeID").alias("employee_id"),
        F.current_timestamp().alias("generated_at")
    ))
)

# Seleccionar solo las columnas necesarias para content_table
df_final = df_content.select(
    "EmployeeID",
    "annotations",
    "meta",
    "text"
)

# Ver resultado
display(df_final.limit(2))

print("✅ Content table generado correctamente")


# ============================================================================
# CELDA 7: GUARDAR TABLA FÍSICA
# 🔧 AJUSTA el nombre de la tabla de salida
# ============================================================================

# 🔧 CAMBIAR ESTE NOMBRE según tu esquema
tabla_salida = 'hr_database.ohr_agent_content_table'

# Guardar como tabla Delta
df_final.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable(tabla_salida)

print(f"✅ Tabla guardada exitosamente: {tabla_salida}")
print(f"📊 Total de registros: {df_final.count()}")


# ============================================================================
# CELDA 8: VERIFICACIÓN FINAL
# Ejecuta esta celda para verificar que todo funcionó
# ============================================================================

# Leer la tabla que acabamos de crear
resultado = spark.table(tabla_salida)

# Mostrar primeros registros
display(resultado.limit(3))

# Estadísticas
print("=" * 60)
print("📊 RESUMEN DE PROCESAMIENTO")
print("=" * 60)
print(f"Total de empleados procesados: {resultado.count()}")
print(f"Columnas en la tabla: {', '.join(resultado.columns)}")

# Verificar que las imágenes se procesaron
con_foto = resultado.filter(F.col("text").contains("<img")).count()
con_placeholder = resultado.filter(F.col("text").contains("👤")).count()

print(f"\n✅ Empleados con foto: {con_foto}")
print(f"⚠️  Empleados con placeholder: {con_placeholder}")
print("=" * 60)

print("\n🎉 ¡PROCESO COMPLETADO!")
print(f"\n📋 Próximos pasos:")
print(f"1. Ve a Fabric Data Agent")
print(f"2. Abre tu agente 'OHR Agent'")
print(f"3. Configura Content Protocol con la tabla: {tabla_salida}")
print(f"4. Mapea: annotations, meta, text")
print(f"5. ¡Prueba tu agente!")
