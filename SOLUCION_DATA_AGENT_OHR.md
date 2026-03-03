# 🎯 Solución: Fabric Data Agent OHR → Copilot Studio con Imágenes

**Tu problema específico**: El Data Agent "OHR Agent" devuelve texto generativo en lugar de datos estructurados para construir el HTML de la imagen.

---

## 📊 **TU ARQUITECTURA ACTUAL**

```
Snowflake (TDS, LMD, SHD)
    ↓
PRD_TDS_GBL_OHR (Mirrored Database)
    ↓
OHR Base64 Image Parser (Notebook)
    ↓
OHR Agent (Fabric Data Agent)
    ↓
Copilot Studio "Datos Aldo" Topic
    ❌ Muestra texto en lugar de imagen
```

---

## 🔍 **¿POR QUÉ FUNCIONA CON `Topic.Base64Aldo` PERO NO CON DATA AGENT?**

### **Configuración actual que FUNCIONA** ✅

```yaml
Topic: Datos Aldo

Nodo 1: Set variable value
  Variable: Topic.Base64Aldo
  Value: "/9j/4AAQSkZJRgABAg..." (base64 hardcodeado)

Nodo 2: Set variable value  
  Variable: Topic.Var1
  Value: $"<img src='data:image/png;base64,{Topic.Base64Aldo}' />"

Nodo 3: Message
  Text: {Topic.Var1}
  
Resultado: ✅ IMAGEN SE MUESTRA
```

### **Lo que probablemente está pasando con Data Agent** ❌

```yaml
Topic con Data Agent:

Nodo: DataAgent_OHR_Agent (Tool)
  Input: userQuestion = "One-liner del empleado con el número 102020"
  
Response del Data Agent:
  "Here is the information for employee 102020:
   Name: Ricardo Morion Perez
   Position: Manager Administration & Support
   <img src='data:image/png;base64,...' />"
   
Problema: El HTML está dentro de texto generativo → Copilot lo escapa
Resultado: ❌ Muestra literal "<img src='data:image/png;base64,...'/>"
```

---

## ✅ **3 SOLUCIONES (de más fácil a más robusta)**

---

## **SOLUCIÓN 1: Extraer Base64 del Data Agent Response** ⚡ (Más rápida)

### **Modificar tu Topic actual**

**ANTES** (no funciona):
```
Trigger
  ↓
DataAgent_OHR_Agent → Topic.AgentResponse
  ↓
Message: {Topic.AgentResponse}
```

**DESPUÉS** (funciona):
```
Trigger
  ↓
DataAgent_OHR_Agent → Topic.AgentResponse
  ↓
Parse Value (Extract base64)
  ↓
Set variable value (Build HTML)
  ↓
Message: {Topic.ImageHTML}
```

### **Paso a paso en Copilot Studio**

#### **Paso 1: Configurar Data Agent para devolver JSON**

En tu Data Agent "OHR Agent", asegúrate de que la respuesta incluya el campo `photo_base64`:

```sql
-- En tu notebook OHR Base64 Image Parser
SELECT 
    employee_id,
    employee_name,
    position,
    department,
    photo_base64,  -- ✅ Este campo debe existir
    oneliner_html  -- Tu contenido actual
FROM OHR_Employee_Data
```

#### **Paso 2: Modificar Topic "Datos Aldo"**

**Nodo 1: Query Data Agent**

```yaml
Tipo: Create generative answers
Nombre: QueryOHRAgent

Connection: OHR Agent (Fabric Data Agent)
Data source: OHR_Employee_Data (o tu tabla)

Input:
  Search term: "employee 102020"  # O Topic.EmployeeNumber
  
Properties:
  ✅ Enable "Include structured data in response"
  
Output:
  → Topic.DataAgentResponse
```

**Nodo 2: Parse JSON Response**

```yaml
Tipo: Parse value
Nombre: ExtractEmployeeData

Parse value from:
  Topic.DataAgentResponse.SearchQueryResult

Output:
  → Topic.EmployeeData
```

**Nodo 3: Extract Base64**

```yaml
Tipo: Set variable value
Nombre: ExtractBase64

Assignments:

Variable: Topic.EmployeeID
To value: Topic.EmployeeData.value[0].employee_id

Variable: Topic.EmployeeName
To value: Topic.EmployeeData.value[0].employee_name

Variable: Topic.Base64Photo
To value: Topic.EmployeeData.value[0].photo_base64
```

**Nodo 4: Build HTML**

```yaml
Tipo: Set variable value
Nombre: BuildImageHTML

Variable: Topic.ImageHTML
To value: $"<img src='data:image/png;base64,{Topic.Base64Photo}' style='max-width:300px;border-radius:8px;' />"
```

**Nodo 5: Show Message**

```yaml
Tipo: Send a message
Nombre: ShowEmployeeWithPhoto

Message:
  {Topic.ImageHTML}
  
  **{Topic.EmployeeName}**
  ID: {Topic.EmployeeID}
```

---

## **SOLUCIÓN 2: Usar Adaptive Card** 🎨 (Mejor práctica)

### **Por qué esta es mejor:**

- ✅ Funciona con URLs HTTP (no solo base64)
- ✅ Diseño profesional consistente
- ✅ No depende de HTML que puede ser escapado
- ✅ Soportado nativamente en Teams, Web Chat, etc.

### **Paso 1: Modificar tu notebook para generar OneLake URLs**

Agrega esta celda a tu notebook **OHR Base64 Image Parser**:

```python
# Celda nueva: Guardar imágenes como archivos
from notebookutils import mssparkutils
import base64

def save_base64_to_lakehouse(base64_string, employee_id):
    """
    Guarda la imagen base64 como archivo .jpg en Lakehouse Files
    Retorna la URL OneLake accesible
    """
    try:
        # Extraer base64 puro (sin data URI prefix)
        if ',' in base64_string:
            base64_data = base64_string.split(',')[1]
        else:
            base64_data = base64_string
            
        # Decodificar
        image_bytes = base64.b64decode(base64_data)
        
        # Path en Lakehouse Files
        file_path = f"/lakehouse/default/Files/employee_photos/{employee_id}.jpg"
        
        # Escribir archivo
        mssparkutils.fs.put(file_path, image_bytes, overwrite=True)
        
        # Generar URL OneLake
        workspace_id = spark.conf.get("trident.workspace.id")
        lakehouse_id = spark.conf.get("trident.lakehouse.id")
        
        onelake_url = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/Files/employee_photos/{employee_id}.jpg"
        
        return onelake_url
    except Exception as e:
        print(f"Error saving image for {employee_id}: {e}")
        return None

# Registrar como UDF
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

save_photo_udf = udf(save_base64_to_lakehouse, StringType())

# Aplicar a tu DataFrame
df_with_urls = df_employees.withColumn(
    "photo_url",
    save_photo_udf("photo_base64", "employee_id")
)

# Guardar en tabla optimizada para Data Agent
df_with_urls.write.format("delta").mode("overwrite").saveAsTable("OHR_Employee_Agent_View")
```

### **Paso 2: Topic con Adaptive Card**

**Nodo 1-3**: Igual que Solución 1 (Query + Parse + Extract)

**Nodo 4: Show Adaptive Card**

```yaml
Tipo: Send a message
Message type: Adaptive Card

Card JSON:
```

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "Employee Profile",
      "weight": "Bolder",
      "size": "Large",
      "color": "Accent"
    },
    {
      "type": "ColumnSet",
      "columns": [
        {
          "type": "Column",
          "width": "auto",
          "items": [
            {
              "type": "Image",
              "url": "${Topic.PhotoURL}",
              "size": "Large",
              "style": "Person"
            }
          ]
        },
        {
          "type": "Column",
          "width": "stretch",
          "items": [
            {
              "type": "TextBlock",
              "text": "${Topic.EmployeeName}",
              "weight": "Bolder",
              "size": "ExtraLarge"
            },
            {
              "type": "FactSet",
              "facts": [
                {
                  "title": "ID:",
                  "value": "${Topic.EmployeeID}"
                },
                {
                  "title": "Position:",
                  "value": "${Topic.Position}"
                },
                {
                  "title": "BU:",
                  "value": "${Topic.BusinessUnit}"
                },
                {
                  "title": "Seniority:",
                  "value": "${Topic.Seniority}"
                },
                {
                  "title": "Tenure:",
                  "value": "${Topic.Tenure}"
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "ActionSet",
      "actions": [
        {
          "type": "Action.Submit",
          "title": "📊 Generate PowerPoint",
          "data": {
            "action": "generate_ppt",
            "employee_id": "${Topic.EmployeeID}"
          }
        }
      ]
    }
  ]
}
```

---

## **SOLUCIÓN 3: API Intermedia para Base64** 🌐 (Para producción)

Si tu Data Agent insiste en devolver texto generativo con HTML escapado, crea un endpoint intermedio.

### **Opción A: Azure Function simple**

```python
# function_app.py
import azure.functions as func
import base64
import json

app = func.FunctionApp()

@app.route(route="employee/photo/{employee_id}", methods=["GET"])
def get_employee_photo(req: func.HttpRequest) -> func.HttpResponse:
    employee_id = req.route_params.get('employee_id')
    
    # Conectar a tu Fabric Data Agent o SQL directamente
    # (usa pyodbc o REST API de Fabric)
    
    connection_string = "Driver={ODBC Driver 18 for SQL Server};..."
    
    import pyodbc
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    query = f"SELECT photo_base64 FROM OHR_Employee_Data WHERE employee_id = '{employee_id}'"
    cursor.execute(query)
    
    row = cursor.fetchone()
    if row:
        base64_photo = row[0]
        
        # Retornar JSON simple
        return func.HttpResponse(
            json.dumps({
                "employee_id": employee_id,
                "photo_base64": base64_photo,
                "photo_data_uri": f"data:image/jpeg;base64,{base64_photo}"
            }),
            mimetype="application/json"
        )
    else:
        return func.HttpResponse("Not found", status_code=404)
```

**Deploy:**

```bash
func init EmployeePhotoAPI --python
cd EmployeePhotoAPI
# Copiar código arriba a function_app.py
func azure functionapp publish employee-photo-api
```

### **Topic con Azure Function**

```yaml
Nodo 1: HTTP Request
  Method: GET
  URL: https://employee-photo-api.azurewebsites.net/api/employee/photo/{Topic.EmployeeID}
  Output → Topic.APIResponse

Nodo 2: Extract Photo
  Topic.Base64Photo = Topic.APIResponse.photo_base64

Nodo 3: Build HTML (igual que Solución 1)
```

---

## 🧪 **DIAGNÓSTICO: ¿Cuál solución necesitas?**

### **Usa SOLUCIÓN 1 si:**
- ✅ Tu Data Agent **YA devuelve** el campo `photo_base64` estructurado
- ✅ Solo necesitas arreglar cómo lo muestras en el Topic
- ⏱️ Tiempo estimado: **15 minutos**

### **Usa SOLUCIÓN 2 si:**
- ✅ Quieres un diseño profesional (mejor que HTML básico)
- ✅ Planeas usar esto en Teams o Mobile
- ✅ Tienes acceso al notebook para agregar la celda de OneLake URLs
- ⏱️ Tiempo estimado: **45 minutos**

### **Usa SOLUCIÓN 3 si:**
- ✅ El Data Agent **NO puede** devolver datos estructurados
- ✅ Solo devuelve texto generativo siempre
- ✅ Tienes permisos para desplegar Azure Functions
- ⏱️ Tiempo estimado: **2 horas**

---

## 🔍 **PRUEBA RÁPIDA: Determinar qué devuelve tu Data Agent**

### **Test en Copilot Studio**

1. En tu Topic "Datos Aldo", después del nodo **DataAgent_OHR_Agent**
2. Agrega nodo temporal: **Send a message**
3. Message: `{json(Topic.AgentResponse)}`
4. Prueba en el chat: `"dame la info de empleado 102020"`

### **Resultados esperados:**

**Caso A: Devuelve JSON estructurado** ✅
```json
{
  "SearchQueryResult": {
    "value": [
      {
        "employee_id": "102020",
        "employee_name": "Ricardo Morion Perez",
        "photo_base64": "/9j/4AAQSkZJRgABAg..."
      }
    ]
  }
}
```
→ **Usar SOLUCIÓN 1**

**Caso B: Devuelve solo texto generativo** ❌
```json
{
  "Answer": "Here is the information for Ricardo Morion Perez...",
  "Citations": [...]
}
```
→ **Usar SOLUCIÓN 3** (o configurar Data Agent diferente)

---

## 📋 **IMPLEMENTACIÓN PASO A PASO (Solución 1 - Recomendada)**

### **1. Verificar tu tabla tiene el campo photo_base64**

```python
# En tu notebook OHR Base64 Image Parser
# Última celda - Verificación

display(df_final.select("employee_id", "employee_name", "photo_base64").limit(5))

# Debe mostrar:
# +-------------+--------------------+-------------------------+
# | employee_id | employee_name      | photo_base64            |
# +-------------+--------------------+-------------------------+
# | 102020      | Ricardo Morion...  | /9j/4AAQSkZJRgABAg...   |
# +-------------+--------------------+-------------------------+
```

### **2. Guardar tabla optimizada**

```python
# Celda final del notebook
df_final.write.format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("OHR_Employee_Agent_View")

print("✅ Tabla OHR_Employee_Agent_View creada")
```

### **3. Actualizar Data Agent**

En Fabric:
1. Ve a **OHR Agent** (Data agent)
2. Settings → Data sources
3. **Remove** la fuente actual
4. **Add** → Select **OHR_Employee_Agent_View**
5. **Save**

### **4. Modificar Topic en Copilot Studio**

Reemplaza los nodos actuales con esta estructura:

```
┌────────────────────────────────┐
│ Trigger                        │
│ "When user asks for Aldo's..."│
└───────────┬────────────────────┘
            │
┌───────────▼────────────────────┐
│ Create generative answers      │
│ Name: QueryOHRAgent            │
│                                │
│ Data source: OHR_Employee_Agent_View │
│ Search: Topic.EmployeeNumber   │
│ Output → Topic.DataResponse    │
└───────────┬────────────────────┘
            │
┌───────────▼────────────────────┐
│ Set variable value             │
│ Name: ExtractData              │
│                                │
│ Topic.EmployeeID =             │
│   Topic.DataResponse.          │
│   SearchQueryResult.           │
│   value[0].employee_id         │
│                                │
│ Topic.EmployeeName =           │
│   Topic.DataResponse.          │
│   SearchQueryResult.           │
│   value[0].employee_name       │
│                                │
│ Topic.Base64Photo =            │
│   Topic.DataResponse.          │
│   SearchQueryResult.           │
│   value[0].photo_base64        │
└───────────┬────────────────────┘
            │
┌───────────▼────────────────────┐
│ Set variable value             │
│ Name: BuildHTML                │
│                                │
│ Topic.ImageHTML = $"<img       │
│   src='data:image/jpeg;base64, │
│   {Topic.Base64Photo}'         │
│   style='max-width:300px;      │
│   border-radius:8px;' />"      │
└───────────┬────────────────────┘
            │
┌───────────▼────────────────────┐
│ Message                        │
│                                │
│ {Topic.ImageHTML}              │
│                                │
│ **{Topic.EmployeeName}**       │
│ ID: {Topic.EmployeeID}         │
└────────────────────────────────┘
```

### **5. Probar**

En el chat de prueba:
```
User: "dame la foto de aldo"
Bot: [Muestra imagen + nombre + ID]
```

---

## 🐛 **TROUBLESHOOTING ESPECÍFICO**

### **Problema: Topic.DataResponse está vacío**

**Causa**: Data Agent no encontró resultados

**Solución**:
```yaml
Después de "Create generative answers", agregar:

Nodo: Condition
  IF Topic.DataResponse.SearchQueryResult.value is empty
  THEN:
    Message: "No encontré información para ese empleado"
    End conversation
  ELSE:
    Continuar con Extract Data
```

### **Problema: `Topic.Base64Photo` está vacío pero otros campos sí tienen valor**

**Causa**: La columna `photo_base64` no existe en la tabla

**Solución**:
```sql
-- Verificar en notebook
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'OHR_Employee_Agent_View'

-- Si no existe photo_base64, usar el nombre correcto (ej: base64_photo, image_data, etc.)
```

### **Problema: Imagen muestra "broken icon" 🖼️❌**

**Causa**: Base64 está corrupto o mal formateado

**Solución**:
```python
# En notebook, agregar validación
from pyspark.sql.functions import when, length

df_final = df_final.withColumn(
    "photo_base64_clean",
    when(
        (col("photo_base64").isNotNull()) & 
        (length(col("photo_base64")) > 100),
        col("photo_base64")
    ).otherwise(None)
)

# Contar cuántas imágenes válidas
df_final.filter(col("photo_base64_clean").isNotNull()).count()
```

### **Problema: HTML se muestra como texto `<img src='data:image...`**

**Causa**: La variable contiene texto escapado

**Solución**:
```yaml
# NO usar este formato:
Topic.ImageHTML = Topic.DataResponse.oneliner_html  # ❌ Viene escapado

# SÍ usar construcción manual:
Topic.ImageHTML = $"<img src='data:image/jpeg;base64,{Topic.Base64Photo}' />"  # ✅
```

---

## 💡 **MEJORAS ADICIONALES**

### **A. Agregar botón para generar PowerPoint**

En el nodo Message final, cambia a **Adaptive Card**:

```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "Image",
      "url": "data:image/jpeg;base64,${Topic.Base64Photo}",
      "size": "Large"
    },
    {
      "type": "TextBlock",
      "text": "${Topic.EmployeeName}",
      "weight": "Bolder"
    }
  ],
  "actions": [
    {
      "type": "Action.Submit",
      "title": "📊 Generar PowerPoint",
      "data": {
        "action": "generate_ppt",
        "employee_id": "${Topic.EmployeeID}"
      }
    }
  ]
}
```

### **B. Caché de imágenes para rendimiento**

Si consultas el mismo empleado múltiples veces:

```yaml
Al inicio del Topic, agregar:

Nodo: Condition
  IF Global.CachedEmployees contains Topic.EmployeeID
  THEN:
    Topic.Base64Photo = Global.CachedEmployees[Topic.EmployeeID]
    Skip to "Build HTML"
  ELSE:
    Continue to "Query Data Agent"

Después de Extract Data:
  Set variable value:
    Global.CachedEmployees[Topic.EmployeeID] = Topic.Base64Photo
```

---

## 📊 **COMPARACIÓN DE SOLUCIONES**

| Aspecto | Solución 1 (Parse JSON) | Solución 2 (Adaptive Card) | Solución 3 (API) |
|---------|------------------------|---------------------------|------------------|
| **Complejidad** | ⭐ Baja | ⭐⭐ Media | ⭐⭐⭐ Alta |
| **Tiempo implementación** | 15 min | 45 min | 2 horas |
| **Diseño visual** | HTML básico | ⭐⭐⭐ Profesional | HTML básico |
| **Rendimiento** | ⭐⭐⭐ Rápido (directo) | ⭐⭐⭐ Rápido | ⭐⭐ Medio (extra hop) |
| **Mantenimiento** | ⭐⭐⭐ Fácil | ⭐⭐ Medio | ⭐ Requiere infraestructura |
| **Funciona en Teams** | ⚠️ Limitado | ⭐⭐⭐ Nativo | ⚠️ Limitado |
| **Funciona en Mobile** | ⚠️ Puede fallar | ⭐⭐⭐ Optimizado | ⚠️ Puede fallar |

**Recomendación**: 
- **Desarrollo/Testing**: Solución 1
- **Producción**: Solución 2
- **Emergencia** (si 1 y 2 fallan): Solución 3

---

## 🎯 **PRÓXIMO PASO INMEDIATO**

Ejecuta esta prueba en tu Topic actual:

```yaml
Después del nodo "DataAgent_OHR_Agent", agregar:

Message (temporal para debugging):
  ```
  **Debug Info:**
  
  Full response: {json(Topic.AgentResponse)}
  
  Type: {TypeOf(Topic.AgentResponse)}
  ```
```

Envíame una captura de pantalla de esa respuesta y te diré **exactamente** cuál solución necesitas y el código específico.

---

¿Quieres que ejecutemos juntos esa prueba de debug? 🔍
