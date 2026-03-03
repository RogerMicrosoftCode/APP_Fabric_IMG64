# ============================================================================
# FABRIC NOTEBOOK: Leer fotos de Snowflake y almacenar en Lakehouse
# Copiar y pegar en Fabric Notebook
# ============================================================================

# ============================================================================
# CELDA 1: INSTALAR DEPENDENCIAS
# ============================================================================

%pip install snowflake-connector-python Pillow==10.2.0


# ============================================================================
# CELDA 2: IMPORTS Y CONFIGURACIÓN
# ============================================================================

from pyspark.sql import functions as F
from pyspark.sql.types import StringType, BinaryType, StructType, StructField
import snowflake.connector
import pandas as pd
import base64
import io
from PIL import Image
import json
from datetime import datetime

# Configuración de Snowflake (usar Key Vault o secretos seguros en producción)
SNOWFLAKE_CONFIG = {
    'account': 'YOUR_ACCOUNT.snowflakecomputing.com',
    'user': 'YOUR_USER',
    'password': 'YOUR_PASSWORD',  # ⚠️ Usar Key Vault en producción
    'warehouse': 'YOUR_WAREHOUSE',
    'database': 'PRD_TDS_OBL_OHR',
    'schema': 'OHR',
    'role': 'YOUR_ROLE'
}


# ============================================================================
# CELDA 3: FUNCIÓN PARA LEER DE SNOWFLAKE
# ============================================================================

def read_snowflake_photos():
    """
    Lee fotos desde Snowflake y retorna DataFrame de Pandas
    """
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    
    query = """
    SELECT 
        employee_id,
        first_name,
        last_name,
        department,
        position,
        photo_url,
        LENGTH(photo_url) as photo_size
    FROM PRD_TDS_OBL_OHR.OHR.VW_TEST_DATABOT_ORIGINAL
    WHERE photo_url IS NOT NULL 
        AND LENGTH(photo_url) > 0
        AND UPPER(first_name || ' ' || last_name) LIKE '%PAMELA YISSELL%'
    LIMIT 100
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    print(f"✅ Leídos {len(df)} registros de Snowflake")
    return df


# ============================================================================
# CELDA 4: FUNCIONES DE PROCESAMIENTO DE IMÁGENES
# ============================================================================

def extract_base64_from_datauri(data_uri):
    """
    Extrae base64 puro de data URI (data:image/jpeg;base64,...)
    """
    if not data_uri or pd.isna(data_uri):
        return None
    
    if ',' in data_uri:
        # Formato: data:image/jpeg;base64,XXXXX
        return data_uri.split(',')[1]
    
    return data_uri


def save_photo_to_lakehouse(employee_id, base64_string, lakehouse_path="Files/employee_photos"):
    """
    Guarda foto en Lakehouse Files como archivo .jpg
    Retorna URL de OneLake
    """
    if not base64_string:
        return None
    
    try:
        # Decodificar base64
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        
        # Redimensionar si es muy grande
        max_size = (800, 800)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Guardar en Lakehouse
        file_path = f"{lakehouse_path}/{employee_id}.jpg"
        
        # Convertir a bytes
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)
        
        # Escribir archivo en Lakehouse
        mssparkutils.fs.put(file_path, buffer.read().decode('latin1'), True)
        
        # Retornar URL de OneLake
        onelake_url = f"https://onelake.dfs.fabric.microsoft.com/{lakehouse_path}/{employee_id}.jpg"
        
        return onelake_url
        
    except Exception as e:
        print(f"❌ Error guardando foto {employee_id}: {e}")
        return None


def create_thumbnail(base64_string, size=(150, 150)):
    """
    Crea thumbnail y retorna nuevo base64
    """
    if not base64_string:
        return None
    
    try:
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=75)
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode('utf-8')
    except:
        return None


# ============================================================================
# CELDA 5: PROCESAR DATOS DE SNOWFLAKE
# ============================================================================

# Leer de Snowflake
df_snowflake = read_snowflake_photos()

# Extraer base64 limpio
df_snowflake['base64_clean'] = df_snowflake['photo_url'].apply(extract_base64_from_datauri)

# Crear thumbnails
df_snowflake['thumbnail_base64'] = df_snowflake['base64_clean'].apply(
    lambda x: create_thumbnail(x, size=(150, 150))
)

# Guardar fotos en Lakehouse
df_snowflake['onelake_url'] = df_snowflake.apply(
    lambda row: save_photo_to_lakehouse(row['employee_id'], row['base64_clean']),
    axis=1
)

# Agregar metadata
df_snowflake['created_at'] = datetime.utcnow()
df_snowflake['source_system'] = 'Snowflake'

print(f"✅ Procesados {len(df_snowflake)} empleados")
display(df_snowflake[['employee_id', 'first_name', 'last_name', 'onelake_url']].head())


# ============================================================================
# CELDA 6: GUARDAR EN DELTA LAKE
# ============================================================================

# Convertir a Spark DataFrame
spark_df = spark.createDataFrame(df_snowflake)

# Crear tabla de registro
spark_df.write.format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("employee_photos_from_snowflake")

print("✅ Tabla Delta creada: employee_photos_from_snowflake")


# ============================================================================
# CELDA 7: CREAR TABLA OPTIMIZADA PARA DATA AGENT
# ============================================================================

# Crear tabla con formato optimizado para Copilot Data Agent
agent_df = spark.sql("""
    SELECT 
        employee_id,
        CONCAT(first_name, ' ', last_name) as employee_name,
        first_name,
        last_name,
        department,
        position,
        onelake_url as photo_url,
        thumbnail_base64,
        CONCAT(
            'Empleado: ', first_name, ' ', last_name, '\\n',
            'Departamento: ', department, '\\n',
            'Posición: ', position, '\\n',
            'ID: ', employee_id
        ) as employee_description
    FROM employee_photos_from_snowflake
    WHERE onelake_url IS NOT NULL
""")

agent_df.write.format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("employee_agent_view")

print("✅ Tabla para Data Agent creada: employee_agent_view")


# ============================================================================
# CELDA 8: VERIFICACIÓN Y ESTADÍSTICAS
# ============================================================================

stats = spark.sql("""
    SELECT 
        COUNT(*) as total_employees,
        COUNT(DISTINCT department) as unique_departments,
        COUNT(photo_url) as photos_available,
        SUM(CASE WHEN thumbnail_base64 IS NOT NULL THEN 1 ELSE 0 END) as thumbnails_created
    FROM employee_agent_view
""")

print("📊 Estadísticas:")
stats.show()

# Mostrar muestra
print("\n🔍 Muestra de datos:")
spark.sql("SELECT * FROM employee_agent_view LIMIT 5").show(truncate=False)

# Información para el Data Agent
print("""
✅ CONFIGURACIÓN PARA DATA AGENT:
===================================
1. Tabla a consultar: employee_agent_view
2. Columnas disponibles:
   - employee_id
   - employee_name (nombre completo)
   - department
   - position
   - photo_url (URL de OneLake)
   - thumbnail_base64 (para vista previa)
   - employee_description (texto descriptivo)

3. Query ejemplo para el agente:
   SELECT employee_name, department, photo_url, employee_description
   FROM employee_agent_view
   WHERE employee_name LIKE '%Pamela%'
""")
