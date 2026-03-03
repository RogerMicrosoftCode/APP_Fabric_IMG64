# 🔧 Guía de Implementación Técnica

> **Manual Paso a Paso para Implementar la Arquitectura de Gestión de Imágenes**  
> **Versión:** 2.0  
> **Fecha:** 3 de Marzo, 2026

---

## 📑 Tabla de Contenidos

1. [Fase 1: Foundation & Migration](#fase-1-foundation--migration)
2. [Fase 2: Agent Integration & Optimization](#fase-2-agent-integration--optimization)
3. [Fase 3: Governance & Production Readiness](#fase-3-governance--production-readiness)
4. [Troubleshooting](#troubleshooting)

---

## Fase 1: Foundation & Migration

**Duración estimada:** 2 semanas  
**Objetivo:** Migrar de Base64 a Lakehouse Files con metadata registry funcional

### 1.1 Crear Estructura de Carpetas en Lakehouse

```python
# ============================================================================
# PASO 1: Estructura de carpetas OneLake
# ============================================================================

# Crear estructura de directorios
folders = [
    "Files/employee_photos/2026/01",
    "Files/employee_photos/2026/02",
    "Files/employee_photos/2026/03",
    "Files/employee_photos/thumbnails",
    "Files/employee_photos/archive"
]

for folder in folders:
    mssparkutils.fs.mkdirs(f"abfss://lakehouse@onelake.dfs.fabric.microsoft.com/{folder}")
    
print("✅ Estructura de carpetas creada")
```

**Verificación:**
```python
# Listar estructura
mssparkutils.fs.ls("Files/employee_photos/")
```

---

### 1.2 Crear Tabla de Metadata Registry

```sql
-- ============================================================================
-- PASO 2: Tabla employee_photo_registry
-- ============================================================================

CREATE TABLE hr_lakehouse.employee_photo_registry (
    photo_id STRING COMMENT 'UUID único de la foto',
    employee_id STRING COMMENT 'Employee ID (FK)',
    photo_url STRING COMMENT 'OneLake path completo',
    thumbnail_url STRING COMMENT 'Thumbnail path',
    content_type STRING COMMENT 'image/jpeg o image/png',
    file_size_bytes BIGINT COMMENT 'Tamaño del archivo',
    width INT COMMENT 'Ancho en píxeles',
    height INT COMMENT 'Alto en píxeles',
    upload_timestamp TIMESTAMP COMMENT 'Fecha de carga',
    last_accessed TIMESTAMP COMMENT 'Último acceso (para lifecycle)',
    source_system STRING COMMENT 'successfactors',
    version INT COMMENT 'Versión de la foto',
    is_current_version BOOLEAN COMMENT 'TRUE solo para version más reciente',
    is_active BOOLEAN COMMENT 'FALSE si eliminada lógicamente',
    storage_tier STRING COMMENT 'hot, warm, cold',
    classification STRING COMMENT 'PII, Confidential',
    created_by STRING COMMENT 'Service Principal',
    updated_timestamp TIMESTAMP COMMENT 'Última modificación'
)
USING DELTA
PARTITIONED BY (DATE_TRUNC('month', upload_timestamp))
COMMENT 'Metadata registry para employee photos';

-- Optimizar con ZORDER
OPTIMIZE hr_lakehouse.employee_photo_registry
ZORDER BY (employee_id);

-- Crear índice Bloom filter para búsquedas rápidas
CREATE BLOOMFILTER INDEX idx_employee_id
ON TABLE hr_lakehouse.employee_photo_registry
FOR COLUMNS(employee_id OPTIONS (FPP=0.1, NDV=100000));
```

**Verificación:**
```sql
DESCRIBE EXTENDED hr_lakehouse.employee_photo_registry;
SHOW PARTITIONS hr_lakehouse.employee_photo_registry;
```

---

### 1.3 Desarrollar Pipeline de Ingesta desde SuccessFactors

```python
# ============================================================================
# PASO 3: Pipeline SuccessFactors → Lakehouse Files
# ============================================================================

import requests
import uuid
from datetime import datetime
from PIL import Image
from io import BytesIO
import base64

# Configuración
SF_BASE_URL = "https://api.successfactors.com/odata/v2"
SF_API_KEY = mssparkutils.credentials.getSecret("kv-fabric", "sf-api-key")

def download_photo_from_successfactors(employee_id: str) -> bytes:
    """
    Descarga foto de SuccessFactors via OData API
    
    Returns:
        bytes: Contenido binario de la imagen
    """
    endpoint = f"{SF_BASE_URL}/EmpJob('{employee_id}')/photoNav"
    
    headers = {
        "Authorization": f"Bearer {SF_API_KEY}",
        "Accept": "application/json"
    }
    
    response = requests.get(endpoint, headers=headers, timeout=30)
    response.raise_for_status()
    
    # SuccessFactors devuelve base64
    photo_base64 = response.json()['d']['photoData']
    photo_bytes = base64.b64decode(photo_base64)
    
    return photo_bytes


def save_photo_to_lakehouse(
    employee_id: str, 
    photo_bytes: bytes,
    upload_date: datetime = None
) -> dict:
    """
    Guarda foto en Lakehouse Files y retorna metadata
    
    Returns:
        dict: Metadata con URLs y dimensiones
    """
    if upload_date is None:
        upload_date = datetime.now()
    
    # Generar paths
    year_month = upload_date.strftime("%Y/%m")
    photo_filename = f"{employee_id}_profile.jpg"
    thumb_filename = f"{employee_id}_profile_thumb.jpg"
    
    photo_path = f"Files/employee_photos/{year_month}/{photo_filename}"
    thumb_path = f"Files/employee_photos/thumbnails/{thumb_filename}"
    
    # Guardar foto original
    mssparkutils.fs.put(
        f"abfss://lakehouse@onelake.dfs.fabric.microsoft.com/{photo_path}",
        photo_bytes,
        overwrite=True
    )
    
    # Crear thumbnail (200x200)
    img = Image.open(BytesIO(photo_bytes))
    img.thumbnail((200, 200), Image.Resampling.LANCZOS)
    
    thumb_buffer = BytesIO()
    img.save(thumb_buffer, format='JPEG', quality=85)
    thumb_bytes = thumb_buffer.getvalue()
    
    mssparkutils.fs.put(
        f"abfss://lakehouse@onelake.dfs.fabric.microsoft.com/{thumb_path}",
        thumb_bytes,
        overwrite=True
    )
    
    # Metadata
    metadata = {
        "photo_id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "photo_url": f"https://onelake.dfs.fabric.microsoft.com/{photo_path}",
        "thumbnail_url": f"https://onelake.dfs.fabric.microsoft.com/{thumb_path}",
        "content_type": "image/jpeg",
        "file_size_bytes": len(photo_bytes),
        "width": img.width,
        "height": img.height,
        "upload_timestamp": upload_date,
        "source_system": "successfactors",
        "version": 1,
        "is_current_version": True,
        "is_active": True,
        "storage_tier": "hot",
        "classification": "PII"
    }
    
    return metadata


def ingest_employee_photos_batch(employee_ids: list):
    """
    Ingesta batch de fotos desde SuccessFactors
    """
    results = []
    
    for emp_id in employee_ids:
        try:
            print(f"Procesando {emp_id}...")
            
            # Download de SuccessFactors
            photo_bytes = download_photo_from_successfactors(emp_id)
            
            # Guardar en Lakehouse
            metadata = save_photo_to_lakehouse(emp_id, photo_bytes)
            
            # Insertar metadata en registry
            spark.createDataFrame([metadata]).write \
                .mode("append") \
                .saveAsTable("hr_lakehouse.employee_photo_registry")
            
            results.append({"employee_id": emp_id, "status": "success"})
            
        except Exception as e:
            print(f"❌ Error con {emp_id}: {str(e)}")
            results.append({"employee_id": emp_id, "status": "failed", "error": str(e)})
    
    return results


# Ejecución
employee_list = spark.sql("""
    SELECT DISTINCT employee_id 
    FROM hr_database.employees 
    WHERE is_active = TRUE
    ORDER BY employee_id
""").collect()

emp_ids = [row.employee_id for row in employee_list]

print(f"📥 Iniciando ingesta de {len(emp_ids)} empleados...")
result_summary = ingest_employee_photos_batch(emp_ids)

# Resumen
success_count = len([r for r in result_summary if r["status"] == "success"])
failed_count = len(result_summary) - success_count

print(f"\n✅ Completado:")
print(f"   - Exitosos: {success_count}")
print(f"   - Fallidos: {failed_count}")
```

**Verificación:**
```sql
SELECT COUNT(*) as total_photos
FROM hr_lakehouse.employee_photo_registry
WHERE is_current_version = TRUE;

-- Validar que todas las fotos son accesibles
SELECT photo_url
FROM hr_lakehouse.employee_photo_registry
LIMIT 5;
```

---

### 1.4 Migrar Datos Existentes (Base64 → Files)

```python
# ============================================================================
# PASO 4: Migración de datos existentes
# ============================================================================

def migrate_base64_to_files():
    """
    Migra fotos existentes en formato Base64 a Lakehouse Files
    """
    # Leer datos actuales
    existing_photos = spark.sql("""
        SELECT 
            employee_id,
            photo_base64,
            upload_date
        FROM hr_database.employees
        WHERE photo_base64 IS NOT NULL
    """).collect()
    
    migrated = 0
    failed = 0
    
    for row in existing_photos:
        try:
            # Decodificar Base64
            photo_bytes = base64.b64decode(row.photo_base64)
            
            # Guardar en Files
            metadata = save_photo_to_lakehouse(
                employee_id=row.employee_id,
                photo_bytes=photo_bytes,
                upload_date=row.upload_date
            )
            
            # Insertar metadata
            spark.createDataFrame([metadata]).write \
                .mode("append") \
                .saveAsTable("hr_lakehouse.employee_photo_registry")
            
            migrated += 1
            
        except Exception as e:
            print(f"❌ Error migrando {row.employee_id}: {e}")
            failed += 1
    
    print(f"\n📊 Migración completada:")
    print(f"   - Migrados: {migrated}")
    print(f"   - Fallidos: {failed}")
    
    return migrated, failed

# Ejecutar migración
migrate_base64_to_files()
```

**Validación post-migración:**
```sql
-- Verificar que todos los empleados tienen foto
SELECT 
    COUNT(DISTINCT e.employee_id) as total_employees,
    COUNT(DISTINCT p.employee_id) as employees_with_photo,
    COUNT(DISTINCT p.employee_id) * 100.0 / COUNT(DISTINCT e.employee_id) as coverage_pct
FROM hr_database.employees e
LEFT JOIN hr_lakehouse.employee_photo_registry p
    ON e.employee_id = p.employee_id
    AND p.is_current_version = TRUE;

-- Resultado esperado: coverage_pct = 100%
```

---

### 1.5 Implementar Row-Level Security (RLS)

```sql
-- ============================================================================
-- PASO 5: Row-Level Security
-- ============================================================================

-- Crear función de seguridad
CREATE OR REPLACE FUNCTION hr_lakehouse.fn_employee_access_filter()
RETURNS TABLE
AS
RETURN
    SELECT DISTINCT p.employee_id
    FROM hr_lakehouse.employee_photo_registry p
    INNER JOIN hr_database.employees e
        ON p.employee_id = e.employee_id
    INNER JOIN hr_database.department_access da
        ON e.department_id = da.department_id
    WHERE da.user_email = CURRENT_USER()
       OR CURRENT_USER() IN (
           SELECT email FROM hr_database.hr_admins
       )
;

-- Aplicar policy a la tabla
CREATE SECURITY POLICY hr_lakehouse.rls_employee_photos
ADD FILTER PREDICATE hr_lakehouse.fn_employee_access_filter()
ON hr_lakehouse.employee_photo_registry
WITH (STATE = ON);

-- Habilitar RLS
ALTER TABLE hr_lakehouse.employee_photo_registry
SET TBLPROPERTIES ('row_security' = 'true');
```

**Testing de RLS:**
```sql
-- Test 1: Usuario de HR (debe ver todo)
EXECUTE AS USER = 'hr_admin@contoso.com';
SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry;
-- Expectativa: 5000

-- Test 2: Usuario de departamento IT (solo IT)
EXECUTE AS USER = 'john.doe@contoso.com';  -- IT department
SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry;
-- Expectativa: 250 (solo IT employees)

-- Test 3: Usuario sin acceso
EXECUTE AS USER = 'external@partner.com';
SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry;
-- Expectativa: 0
```

---

### 1.6 Crear Content Table para Workbooks

```sql
-- ============================================================================
-- PASO 6: Content Table para Workbooks
-- ============================================================================

CREATE OR REPLACE TABLE hr_lakehouse.workbook_employee_content AS
SELECT 
    e.employee_id,
    e.full_name,
    e.email,
    e.job_title,
    e.department,
    e.hire_date,
    p.photo_url,
    p.thumbnail_url,
    -- HTML pre-renderizado para Workbooks
    CONCAT(
        '<div class="employee-card">',
        '  <img src="', p.thumbnail_url, '" ',
        '       alt="', e.full_name, '" ',
        '       style="width:150px;height:150px;border-radius:50%;object-fit:cover;" />',
        '  <h3>', e.full_name, '</h3>',
        '  <p>', e.job_title, '</p>',
        '</div>'
    ) AS photo_html,
    -- Metadata JSON para APIs
    TO_JSON(STRUCT(
        p.photo_id,
        p.photo_url,
        p.thumbnail_url,
        p.width,
        p.height,
        p.file_size_bytes
    )) AS photo_metadata_json,
    CURRENT_TIMESTAMP() AS generated_at
FROM hr_database.employees e
LEFT JOIN hr_lakehouse.employee_photo_registry p
    ON e.employee_id = p.employee_id
    AND p.is_current_version = TRUE
    AND p.is_active = TRUE
WHERE e.is_active = TRUE;

-- Optimizar para queries rápidos
OPTIMIZE hr_lakehouse.workbook_employee_content
ZORDER BY (employee_id, department);

-- Crear vista para Workbook
CREATE OR REPLACE VIEW hr_lakehouse.v_workbook_employees AS
SELECT 
    employee_id,
    full_name,
    job_title,
    department,
    photo_html,
    hire_date
FROM hr_lakehouse.workbook_employee_content
ORDER BY department, full_name;
```

**Configurar Workbook:**
1. Crear nuevo Workbook en Fabric
2. Conectar a `hr_lakehouse.v_workbook_employees`
3. Agregar columna HTML con `photo_html`
4. Configurar lazy loading: `Settings → Performance → Lazy Load Images`

**Testing:**
```sql
-- Verificar que HTML está bien formado
SELECT photo_html
FROM hr_lakehouse.workbook_employee_content
LIMIT 3;

-- Performance check
SELECT AVG(LENGTH(photo_html)) as avg_html_size_bytes
FROM hr_lakehouse.workbook_employee_content;
-- Expectativa: <2KB por registro
```

---

### 1.7 Criterios de Aceptación Fase 1

Validar TODOS estos puntos antes de continuar a Fase 2:

- [ ] **Datos migrados:** 100% de fotos convertidas de Base64 a Files
- [ ] **Integridad:** `COUNT(*)` en registry = `COUNT(*)` en tabla original
- [ ] **Accesibilidad:** Todas las URLs de `photo_url` responden HTTP 200
- [ ] **Performance:** Query latency <150ms para búsqueda por employee_id
- [ ] **Seguridad:** RLS funciona correctamente (validar con 3 usuarios diferentes)
- [ ] **Workbooks:** Vista renderiza correctamente con imágenes
- [ ] **Zero data loss:** Backup de tabla original creado y verificado

```python
# Script de validación automática
def validate_phase_1():
    checks = {}
    
    # Check 1: Migración completa
    original_count = spark.sql("SELECT COUNT(*) FROM hr_database.employees WHERE photo_base64 IS NOT NULL").first()[0]
    migrated_count = spark.sql("SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry WHERE is_current_version = TRUE").first()[0]
    checks["migration_complete"] = (original_count == migrated_count)
    
    # Check 2: URLs accesibles
    sample_urls = spark.sql("SELECT photo_url FROM hr_lakehouse.employee_photo_registry LIMIT 10").collect()
    accessible = all([requests.head(url.photo_url).status_code == 200 for url in sample_urls])
    checks["urls_accessible"] = accessible
    
    # Check 3: Performance
    import time
    start = time.time()
    spark.sql("SELECT * FROM hr_lakehouse.employee_photo_registry WHERE employee_id = '102025'").first()
    latency = (time.time() - start) * 1000
    checks["performance_ok"] = (latency < 150)
    
    # Reporte
    print("\n📊 Validación Fase 1:")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    all_passed = all(checks.values())
    return all_passed

# Ejecutar
if validate_phase_1():
    print("\n✅ Fase 1 completada exitosamente. Proceder a Fase 2.")
else:
    print("\n❌ Fase 1 tiene problemas. Revisar logs.")
```

---

## Fase 2: Agent Integration & Optimization

**Duración estimada:** 2 semanas  
**Objetivo:** API funcional para agentes IA con caching layer

### 2.1 Desarrollar API para Agentes IA

```python
# ============================================================================
# PASO 7: FabricImageAgentAPI
# ============================================================================

from typing import Optional, List, Dict
import json

class FabricImageAgentAPI:
    """
    API para que agentes de IA consuman imágenes de empleados
    """
    
    def __init__(self, lakehouse_name: str = "hr_lakehouse"):
        self.lakehouse = lakehouse_name
        
    def get_employee_photo(
        self, 
        employee_id: str,
        size: str = "full"  # "full" o "thumbnail"
    ) -> Dict:
        """
        Obtiene foto de un empleado por ID
        
        Args:
            employee_id: Employee ID
            size: "full" o "thumbnail"
            
        Returns:
            Dict con URL, metadata y HTML
        """
        query = f"""
            SELECT 
                photo_id,
                employee_id,
                {'photo_url' if size == 'full' else 'thumbnail_url'} as url,
                content_type,
                file_size_bytes,
                width,
                height,
                classification
            FROM {self.lakehouse}.employee_photo_registry
            WHERE employee_id = '{employee_id}'
              AND is_current_version = TRUE
              AND is_active = TRUE
        """
        
        result = spark.sql(query).first()
        
        if not result:
            return {
                "success": False,
                "error": f"No photo found for employee_id: {employee_id}"
            }
        
        # Registrar acceso para analytics
        self._log_access(employee_id)
        
        return {
            "success": True,
            "photo_id": result.photo_id,
            "employee_id": result.employee_id,
            "url": result.url,
            "content_type": result.content_type,
            "file_size_bytes": result.file_size_bytes,
            "dimensions": {
                "width": result.width,
                "height": result.height
            },
            "classification": result.classification
        }
    
    def search_employees_with_photos(
        self,
        department: Optional[str] = None,
        job_title_pattern: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Busca empleados con fotos por criterios
        """
        filters = ["p.is_current_version = TRUE", "p.is_active = TRUE"]
        
        if department:
            filters.append(f"e.department = '{department}'")
        if job_title_pattern:
            filters.append(f"e.job_title LIKE '%{job_title_pattern}%'")
        
        where_clause = " AND ".join(filters)
        
        query = f"""
            SELECT 
                e.employee_id,
                e.full_name,
                e.email,
                e.job_title,
                e.department,
                p.thumbnail_url as photo_url
            FROM {self.lakehouse}.employee_photo_registry p
            INNER JOIN hr_database.employees e
                ON p.employee_id = e.employee_id
            WHERE {where_clause}
            ORDER BY e.full_name
            LIMIT {limit}
        """
        
        results = spark.sql(query).collect()
        
        return [
            {
                "employee_id": r.employee_id,
                "full_name": r.full_name,
                "email": r.email,
                "job_title": r.job_title,
                "department": r.department,
                "photo_url": r.photo_url
            }
            for r in results
        ]
    
    def get_batch_photos(
        self,
        employee_ids: List[str],
        size: str = "thumbnail"
    ) -> List[Dict]:
        """
        Obtiene fotos para múltiples empleados (batch)
        Optimizado para reduce latencia en bulk operations
        """
        ids_str = "','".join(employee_ids)
        url_field = 'photo_url' if size == 'full' else 'thumbnail_url'
        
        query = f"""
            SELECT 
                employee_id,
                {url_field} as url,
                file_size_bytes
            FROM {self.lakehouse}.employee_photo_registry
            WHERE employee_id IN ('{ids_str}')
              AND is_current_version = TRUE
              AND is_active = TRUE
        """
        
        results = spark.sql(query).collect()
        
        # Batch access log
        for emp_id in employee_ids:
            self._log_access(emp_id)
        
        return [
            {
                "employee_id": r.employee_id,
                "url": r.url,
                "file_size_bytes": r.file_size_bytes
            }
            for r in results
        ]
    
    def _log_access(self, employee_id: str):
        """
        Registra acceso a foto para compliance y analytics
        """
        log_entry = {
            "access_id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "accessed_by": spark.sql("SELECT CURRENT_USER()").first()[0],
            "access_timestamp": datetime.now(),
            "access_type": "api_read"
        }
        
        spark.createDataFrame([log_entry]).write \
            .mode("append") \
            .saveAsTable(f"{self.lakehouse}.photo_access_audit")


# Uso desde Agente IA
api = FabricImageAgentAPI()

# Get single photo
photo_data = api.get_employee_photo("102025", size="thumbnail")
print(photo_data["url"])

# Search by department
it_employees = api.search_employees_with_photos(department="IT", limit=20)

# Batch get
employee_batch = ["102025", "102026", "102027"]
photos = api.get_batch_photos(employee_batch)
```

---

### 2.2 Implementar Caching con Redis

```python
# ============================================================================
# PASO 8: Redis Cache Layer
# ============================================================================

import redis
import json
from datetime import timedelta

class CachedImageAPI:
    """
    Wrapper sobre FabricImageAgentAPI con Redis cache
    """
    
    def __init__(self, redis_host: str, redis_port: int = 6379):
        self.api = FabricImageAgentAPI()
        self.cache = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            decode_responses=True
        )
        self.cache_ttl = timedelta(hours=1)  # TTL = 1 hora
        
    def get_employee_photo(self, employee_id: str, size: str = "full") -> Dict:
        """
        Get photo con cache-aside pattern
        """
        cache_key = f"photo:{employee_id}:{size}"
        
        # Try cache first
        cached = self.cache.get(cache_key)
        if cached:
            print(f"✅ Cache HIT: {cache_key}")
            return json.loads(cached)
        
        # Cache miss → fetch from DB
        print(f"⚠️ Cache MISS: {cache_key}")
        photo_data = self.api.get_employee_photo(employee_id, size)
        
        # Store in cache
        if photo_data["success"]:
            self.cache.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(photo_data)
            )
        
        return photo_data
    
    def invalidate_cache(self, employee_id: str):
        """
        Invalida cache cuando se actualiza foto
        """
        keys = [
            f"photo:{employee_id}:full",
            f"photo:{employee_id}:thumbnail"
        ]
        self.cache.delete(*keys)
        print(f"🗑️ Cache invalidated for: {employee_id}")
    
    def get_cache_stats(self) -> Dict:
        """
        Métricas de cache
        """
        info = self.cache.info("stats")
        
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        return {
            "hits": hits,
            "misses": misses,
            "hit_rate_pct": round(hit_rate, 2),
            "total_keys": self.cache.dbsize()
        }


# Setup Redis (ejecutar una vez)
# Azure Cache for Redis o Redis local
REDIS_HOST = "your-redis.redis.cache.windows.net"

# Uso
cached_api = CachedImageAPI(redis_host=REDIS_HOST)

# First call → Cache MISS
photo1 = cached_api.get_employee_photo("102025")

# Second call → Cache HIT (latency mejora 10x)
photo2 = cached_api.get_employee_photo("102025")

# Monitorear performance
stats = cached_api.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate_pct']}%")
# Target: >80%
```

**Configurar Redis en Azure:**
```bash
# Azure CLI
az redis create \
  --resource-group rg-fabric-prod \
  --name redis-employee-photos \
  --location eastus \
  --sku Standard \
  --vm-size C1 \
  --enable-non-ssl-port false
```

---

### 2.3 Implementar Audit Logging

```sql
-- ============================================================================
-- PASO 9: Audit Logging
-- ============================================================================

CREATE TABLE hr_lakehouse.photo_access_audit (
    access_id STRING COMMENT 'UUID del acceso',
    employee_id STRING COMMENT 'Empleado cuya foto fue accedida',
    accessed_by STRING COMMENT 'Usuario o service principal',
    access_timestamp TIMESTAMP COMMENT 'Timestamp del acceso',
    access_type STRING COMMENT 'api_read, workbook_view, export',
    request_ip STRING COMMENT 'IP del request',
    user_agent STRING COMMENT 'User agent del cliente',
    response_status STRING COMMENT 'success, denied, not_found',
    latency_ms INT COMMENT 'Latencia del request'
)
USING DELTA
PARTITIONED BY (DATE_TRUNC('day', access_timestamp))
COMMENT 'Audit log para accesos a employee photos';

-- Retención: 2 años para compliance
ALTER TABLE hr_lakehouse.photo_access_audit
SET TBLPROPERTIES ('delta.logRetentionDuration' = '730 days');
```

**Query de compliance:**
```sql
-- ¿Quién accedió a la foto de un empleado específico?
SELECT 
    access_timestamp,
    accessed_by,
    access_type,
    request_ip
FROM hr_lakehouse.photo_access_audit
WHERE employee_id = '102025'
  AND access_timestamp >= CURRENT_DATE - INTERVAL 30 DAYS
ORDER BY access_timestamp DESC;

-- Top 10 usuarios con más accesos
SELECT 
    accessed_by,
    COUNT(*) as access_count,
    COUNT(DISTINCT employee_id) as unique_employees_accessed
FROM hr_lakehouse.photo_access_audit
WHERE access_timestamp >= CURRENT_DATE - INTERVAL 7 DAYS
GROUP BY accessed_by
ORDER BY access_count DESC
LIMIT 10;
```

---

### 2.4 Performance Testing

```python
# ============================================================================
# PASO 10: Performance Benchmarks
# ============================================================================

import time
import statistics

def benchmark_api_latency(api, employee_ids: List[str], iterations: int = 100):
    """
    Mide latencia de API calls
    """
    latencies = []
    
    for i in range(iterations):
        emp_id = employee_ids[i % len(employee_ids)]
        
        start = time.time()
        api.get_employee_photo(emp_id, size="thumbnail")
        latency = (time.time() - start) * 1000  # ms
        
        latencies.append(latency)
    
    return {
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2),  # 95th percentile
        "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 2),
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2)
    }

# Test sin cache
test_ids = ["102025", "102026", "102027", "102028", "102029"]
uncached_api = FabricImageAgentAPI()
results_uncached = benchmark_api_latency(uncached_api, test_ids)

# Test con cache
cached_api = CachedImageAPI(redis_host=REDIS_HOST)
results_cached = benchmark_api_latency(cached_api, test_ids)

# Comparar
print("\n📊 Performance Benchmark:")
print(f"\nSin Cache:")
print(f"   - Latencia promedio: {results_uncached['mean_ms']} ms")
print(f"   - P95: {results_uncached['p95_ms']} ms")
print(f"\nCon Cache:")
print(f"   - Latencia promedio: {results_cached['mean_ms']} ms")
print(f"   - P95: {results_cached['p95_ms']} ms")
print(f"\nMejora: {round((1 - results_cached['p95_ms']/results_uncached['p95_ms']) * 100, 1)}%")

# Targets:
# - P95 sin cache: <150ms
# - P95 con cache: <50ms
```

---

### 2.5 Criterios de Aceptación Fase 2

- [ ] **API funcional:** Todos los métodos de `FabricImageAgentAPI` funcionan
- [ ] **Cache operativo:** Redis configurado y hit rate >75%
- [ ] **Performance:** P95 latency <100ms con cache
- [ ] **Audit completo:** 100% de accesos logged en `photo_access_audit`
- [ ] **Batch performance:** `get_batch_photos(20)` completa en <1s
- [ ] **Integration testing:** Agente IA puede consumir fotos exitosamente

---

## Fase 3: Governance & Production Readiness

**Duración estimada:** 1 semana  
**Objetivo:** Sistema production-ready con governance completo

### 3.1 Implementar ABAC (Attribute-Based Access Control)

```sql
-- ============================================================================
-- PASO 11: ABAC Policies
-- ============================================================================

-- Crear función ABAC
CREATE OR REPLACE FUNCTION hr_lakehouse.fn_abac_filter()
RETURNS TABLE
AS
RETURN
    SELECT DISTINCT p.employee_id
    FROM hr_lakehouse.employee_photo_registry p
    WHERE 
        -- Rule 1: Classification-based access
        (
            p.classification = 'Public'
            OR (
                p.classification = 'PII' 
                AND CURRENT_USER() IN (SELECT email FROM hr_database.authorized_users WHERE role IN ('HR_Admin', 'Manager'))
            )
            OR (
                p.classification = 'Confidential'
                AND CURRENT_USER() IN (SELECT email FROM hr_database.authorized_users WHERE role = 'HR_Admin')
            )
        )
        -- Rule 2: Time-based access (business hours only for non-admins)
        AND (
            CURRENT_USER() IN (SELECT email FROM hr_database.hr_admins)
            OR HOUR(CURRENT_TIMESTAMP()) BETWEEN 8 AND 18
        )
;

-- Aplicar ABAC policy
CREATE SECURITY POLICY hr_lakehouse.abac_employee_photos
ADD FILTER PREDICATE hr_lakehouse.fn_abac_filter()
ON hr_lakehouse.employee_photo_registry
WITH (STATE = ON);
```

**Testing ABAC:**
```sql
-- Test 1: Usuario regular en horario laboral
EXECUTE AS USER = 'employee@contoso.com';
SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry WHERE classification = 'PII';
-- Expectativa: 0 (no tiene acceso a PII)

-- Test 2: HR Manager en horario laboral
EXECUTE AS USER = 'hr_manager@contoso.com';
SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry WHERE classification = 'PII';
-- Expectativa: 5000 (acceso completo a PII)

-- Test 3: HR Admin fuera de horario
EXECUTE AS USER = 'hr_admin@contoso.com';
SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry;
-- Expectativa: 5000 (admins siempre tienen acceso)
```

---

### 3.2 Integración con Microsoft Purview

```python
# ============================================================================
# PASO 12: Purview Integration
# ============================================================================

from azure.purview.catalog import PurviewCatalogClient
from azure.identity import DefaultAzureCredential

# Setup
credential = DefaultAzureCredential()
purview_endpoint = "https://your-purview.purview.azure.com"
client = PurviewCatalogClient(endpoint=purview_endpoint, credential=credential)

def register_assets_in_purview():
    """
    Registra assets en Purview para data governance
    """
    # Definir asset para employee_photo_registry
    asset = {
        "typeName": "azure_datalake_gen2_resource_set",
        "attributes": {
            "qualifiedName": "https://onelake.dfs.fabric.microsoft.com/hr_lakehouse/employee_photo_registry",
            "name": "employee_photo_registry",
            "description": "Employee photo metadata registry",
            "classifications": [
                {"typeName": "MICROSOFT.PERSONAL.PII"},
                {"typeName": "MICROSOFT.GOVERNMENT.EU_GDPR"}
            ],
            "contacts": [
                {
                    "contactType": "Expert",
                    "emailAddress": "datagovernance@contoso.com"
                }
            ]
        }
    }
    
    # Crear asset
    response = client.entity.create_or_update(entity=asset)
    print(f"✅ Asset registrado: {response['guid']}")
    
    # Aplicar lineage (SuccessFactors → Registry → Workbook)
    lineage = {
        "typeName": "Process",
        "attributes": {
            "name": "SuccessFactors Photo Ingestion",
            "inputs": [{"typeName": "successfactors_employee", "guid": "..."}],
            "outputs": [{"typeName": "azure_datalake_gen2", "guid": response['guid']}]
        }
    }
    
    client.entity.create_or_update(entity=lineage)
    print("✅ Lineage configurado")

register_assets_in_purview()
```

---

### 3.3 Lifecycle Management Automation

```python
# ============================================================================
# PASO 13: Lifecycle Automation
# ============================================================================

from datetime import datetime, timedelta

def archive_old_photos():
    """
    Archiva fotos no accedidas en 180 días a tier frío
    Ejecutar como notebook scheduled job (diario)
    """
    cutoff_date = datetime.now() - timedelta(days=180)
    
    # Identificar candidatos
    candidates = spark.sql(f"""
        SELECT employee_id, photo_url
        FROM hr_lakehouse.employee_photo_registry
        WHERE last_accessed < '{cutoff_date}'
          AND storage_tier = 'hot'
          AND is_active = TRUE
    """).collect()
    
    print(f"📦 Archivando {len(candidates)} fotos...")
    
    for photo in candidates:
        try:
            # Mover archivo
            source_path = photo.photo_url.replace("https://onelake.dfs.fabric.microsoft.com/", "")
            archive_path = source_path.replace("/employee_photos/", "/employee_photos/archive/")
            
            mssparkutils.fs.mv(source_path, archive_path)
            
            # Actualizar metadata
            spark.sql(f"""
                UPDATE hr_lakehouse.employee_photo_registry
                SET 
                    photo_url = 'https://onelake.dfs.fabric.microsoft.com/{archive_path}',
                    storage_tier = 'cold',
                    archived_date = CURRENT_DATE
                WHERE employee_id = '{photo.employee_id}'
                  AND is_current_version = TRUE
            """)
            
        except Exception as e:
            print(f"❌ Error archivando {photo.employee_id}: {e}")
    
    print(f"✅ Archivado completado")

# Ejecutar (configurar como job diario)
archive_old_photos()
```

**Configurar como Fabric Notebook Job:**
```python
# En portal de Fabric:
# 1. Notebooks → Schedule
# 2. Frequency: Daily at 2 AM
# 3. Notebook: lifecycle_management.ipynb
```

---

### 3.4 Monitoring & Alerting

```python
# ============================================================================
# PASO 14: Monitoring Dashboard
# ============================================================================

# KPI Dashboard SQL
kpi_queries = """
-- KPI 1: Cache Hit Rate
SELECT 
    DATE_TRUNC('hour', access_timestamp) as hour,
    COUNT(*) as total_requests,
    SUM(CASE WHEN latency_ms < 50 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as cache_hit_rate_pct
FROM hr_lakehouse.photo_access_audit
WHERE access_timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
GROUP BY hour
ORDER BY hour DESC;

-- KPI 2: API Latency (P95)
SELECT 
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency_ms
FROM hr_lakehouse.photo_access_audit
WHERE access_timestamp >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR;

-- KPI 3: Error Rate
SELECT 
    response_status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () as percentage
FROM hr_lakehouse.photo_access_audit
WHERE access_timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
GROUP BY response_status;

-- KPI 4: Storage Usage
SELECT 
    storage_tier,
    COUNT(*) as photo_count,
    SUM(file_size_bytes) / 1024 / 1024 / 1024 as total_gb
FROM hr_lakehouse.employee_photo_registry
WHERE is_active = TRUE
GROUP BY storage_tier;
"""
```

**Configurar Alertas:**
```yaml
# Application Insights Alerts (Azure Monitor)

alerts:
  - name: "High API Latency"
    condition: "P95 latency > 200ms"
    query: |
      photo_access_audit
      | where timestamp > ago(5m)
      | summarize p95_latency = percentile(latency_ms, 95)
      | where p95_latency > 200
    severity: 2
    action: email to oncall@contoso.com
    
  - name: "Low Cache Hit Rate"
    condition: "Hit rate < 70%"
    query: |
      photo_access_audit
      | where timestamp > ago(15m)
      | extend is_cache_hit = (latency_ms < 50)
      | summarize hit_rate = avg(todouble(is_cache_hit)) * 100
      | where hit_rate < 70
    severity: 3
    action: slack #fabric-alerts
    
  - name: "High Error Rate"
    condition: "Error rate > 5%"
    query: |
      photo_access_audit
      | where timestamp > ago(5m)
      | summarize error_rate = countif(response_status != 'success') * 100.0 / count()
      | where error_rate > 5
    severity: 1
    action: pagerduty
```

---

### 3.5 Production Readiness Checklist

#### Security (30% weighting)
- [ ] Row-Level Security (RLS) configurado y tested
- [ ] Attribute-Based Access Control (ABAC) implementado
- [ ] Audit logging activo (100% coverage)
- [ ] Data classification aplicada (PII, Confidential)
- [ ] Microsoft Purview integration completa
- [ ] Encriptación at-rest y in-transit habilitada
- [ ] Service Principal con least-privilege access
- [ ] Secrets en Azure Key Vault (zero hardcoded credentials)
- [ ] Penetration testing ejecutado y issues resueltos
- [ ] GDPR compliance validado

#### Performance (25% weighting)
- [ ] Cache hit rate >80%
- [ ] P95 API latency <100ms
- [ ] Workbook load time <2s
- [ ] Batch operations (20 photos) <1s
- [ ] Database indexes optimizados (ZORDER)
- [ ] Thumbnail generation <500ms per image
- [ ] CDN configurado (opcional pero recomendado)
- [ ] Load testing: 1000 concurrent users, <5% error rate

#### Reliability (20% weighting)
- [ ] Backup strategy definida (RPO <1h, RTO <4h)
- [ ] Disaster recovery plan tested
- [ ] High availability configurado (multi-region)
- [ ] Monitoring dashboards creados
- [ ] Alerts configuradas (latency, errors, capacity)
- [ ] Runbooks documentados (incident response)
- [ ] Zero critical bugs en production

#### Operations (15% weighting)
- [ ] Lifecycle management automatizado
- [ ] Documentación técnica completa
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Onboarding guide para nuevos developers
- [ ] Rollback plan documentado
- [ ] Change management process definido

#### Testing (10% weighting)
- [ ] Unit tests: >80% code coverage
- [ ] Integration tests ejecutados
- [ ] UAT completado con usuarios reales
- [ ] Performance benchmarks documentados
- [ ] Security testing (OWASP Top 10)

**Scoring:**
- **90-100%:** ✅ Ready for production
- **75-89%:** ⚠️ Minor issues, can proceed with risk acceptance
- **<75%:** ❌ Not ready, must resolve blockers

---

## Troubleshooting

### Problema: Latencia alta (>200ms)

**Diagnóstico:**
```sql
-- Verificar slow queries
SELECT 
    employee_id,
    AVG(latency_ms) as avg_latency,
    COUNT(*) as request_count
FROM hr_lakehouse.photo_access_audit
WHERE access_timestamp >= CURRENT_TIMESTAMP - INTERVAL 1 HOUR
GROUP BY employee_id
HAVING AVG(latency_ms) > 200
ORDER BY avg_latency DESC
LIMIT 10;
```

**Soluciones:**
1. Verificar cache: `cached_api.get_cache_stats()`
2. Optimizar índices: `OPTIMIZE TABLE ... ZORDER BY (employee_id)`
3. Revisar query plan: `EXPLAIN SELECT ...`
4. Escalar Redis tier si hit rate bajo

---

### Problema: RLS no funciona

**Diagnóstico:**
```sql
-- Verificar policy activa
SELECT * FROM sys.security_policies 
WHERE name = 'rls_employee_photos';

-- Test con diferentes usuarios
EXECUTE AS USER = 'test@contoso.com';
SELECT COUNT(*) FROM hr_lakehouse.employee_photo_registry;
```

**Soluciones:**
1. Verificar función de filtro: `SELECT * FROM hr_lakehouse.fn_employee_access_filter()`
2. Validar permisos en tabla `department_access`
3. Recrear policy si fue modificada

---

### Problema: Cache hit rate bajo (<70%)

**Diagnóstico:**
```python
stats = cached_api.get_cache_stats()
print(f"Hit rate: {stats['hit_rate_pct']}%")
print(f"Total keys: {stats['total_keys']}")
```

**Soluciones:**
1. Aumentar TTL de cache (actualmente 1h)
2. Pre-warm cache con empleados más consultados
3. Verificar eviction policy de Redis
4. Escalar Redis memory capacity

---

### Problema: Purview no muestra lineage

**Diagnóstico:**
```python
# Verificar asset registrado
assets = client.entity.query_using_dsl(
    "from DataSet where name = 'employee_photo_registry'"
)
print(assets)
```

**Soluciones:**
1. Re-ejecutar `register_assets_in_purview()`
2. Validar credentials de Purview
3. Verificar permissions en Purview (Data Curator role requerido)

---

## Resumen de Comandos Críticos

```bash
# Validación rápida del sistema
python validate_all_phases.py

# Monitorear performance en tiempo real
tail -f /logs/api_latency.log

# Invalidar cache para un empleado
python invalidate_cache.py --employee_id 102025

# Trigger manual de archiving
python archive_old_photos.py --dry-run

# Verificar health del sistema
curl https://api.fabric.com/health
```

---

**Documento generado por el equipo de Arquitectura de Datos - Microsoft Fabric**  
*Última actualización: 3 de Marzo, 2026*
