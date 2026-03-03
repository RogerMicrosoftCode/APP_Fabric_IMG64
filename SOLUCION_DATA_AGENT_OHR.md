# 🎯 Solución: OHR Agent con Adaptive Cards en Copilot Studio

**Guía paso a paso para mostrar imágenes de empleados en Copilot Studio usando Fabric Data Agent + Adaptive Cards**

---

## 📊 Tu Arquitectura Actual

```
Snowflake (TDS, LMD, SHD)
    ↓
PRD_TDS_GBL_OHR (Mirrored Database)
    ↓
OHR Base64 Image Parser (Notebook)
    ↓
OHR Agent (Fabric Data Agent)
    ↓
Copilot Studio "Datos Aldo"
    ❌ PROBLEMA: Imágenes se muestran como texto
```

##🔍 Problema Identificado

### ✅ Lo que SÍ funciona en tu Topic actual:

```yaml
Variable hardcodeada:
  Topic.Base64Aldo = "/9j/4AAQSkZJRgABAg..." (base64 completo)
  
Fórmula HTML:
  Topic.Var1 = $"<img src='data:image/png;base64,{Topic.Base64Aldo}' />"

Resultado: ✅ IMAGEN SE MUESTRA
```

### ❌ Lo que NO funciona con Data Agent:

```yaml
Data Agent Response:
  Devuelve texto generativo con HTML escapado
  
Copilot muestra:
  "&lt;img src='data:image...'&gt;" (literal, no renderizado)

Problema: El Data Agent no devuelve datos estructurados que puedas usar en tu fórmula HTML
```

---

## ✅ La Solución: Adaptive Cards con URLs OneLake

### Por qué Adaptive Cards

- ✅ Funciona con URLs HTTP (no depende de base64 en variables)
- ✅ Diseño profesional y consistente
- ✅ Nativo en Copilot Studio, Teams, Mobile
- ✅ No se escapa como HTML
- ✅ Soporta imágenes desde OneLake Files

---

## 🛠️ Implementación Paso a Paso

### **PASO 1: Modificar tu Notebook "OHR Base64 Image Parser"**

Agrega esta nueva celda **AL FINAL** de tu notebook:

```python
# ===================================================================
# CELDA NUEVA: Guardar imágenes como archivos JPG en Lakehouse
# ===================================================================

from notebookutils import mssparkutils
import base64
from pyspark.sql.functions import udf, col
from pyspark.sql.types import StringType

def save_base64_to_lakehouse(base64_string, employee_id):
    """
    Guarda imagen base64 como archivo JPG en Lakehouse Files
    Retorna URL OneLake accesible
    """
    try:
        # Extraer base64 puro (quitar data URI prefix si existe)
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
        
        # Obtener IDs del workspace y lakehouse
        workspace_id = spark.conf.get("trident.workspace.id")
        lakehouse_id = spark.conf.get("trident.lakehouse.id")
        
        # Generar URL OneLake
        onelake_url = f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/Files/employee_photos/{employee_id}.jpg"
        
        return onelake_url
    
    except Exception as e:
        print(f"❌ Error saving image for {employee_id}: {e}")
        return None

# Registrar como UDF para usar con PySpark
save_photo_udf = udf(save_base64_to_lakehouse, StringType())

# Aplicar a tu DataFrame existente
# Asumiendo que tu DataFrame se llama 'df_employees' y tiene columnas:
# - employee_id
# - employee_name
# - photo_base64 (o como se llame tu columna de base64)

df_with_urls = df_employees.withColumn(
    "photo_url",
    save_photo_udf(col("photo_base64"), col("employee_id"))
)

# Crear tabla optimizada para Data Agent
df_with_urls.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .saveAsTable("OHR_Employee_Agent_View")

print("✅ Tabla OHR_Employee_Agent_View creada con éxito")
print(f"✅ Total empleados: {df_with_urls.count()}")

# Mostrar muestra
display(df_with_urls.select(
    "employee_id", 
    "employee_name", 
    "position",
    "department",
    "photo_url"
).limit(10))
```

**Ejecuta el notebook completo** para que se creen los archivos JPG en Lakehouse Files.

---

### **PASO 2: Verificar Archivos Creados**

1. En Fabric, navega a tu **Lakehouse**
2. Ve a **Files** → `employee_photos/`
3. Deberías ver archivos: `102020.jpg`, `102025.jpg`, etc.

**Verificación SQL:**

```sql
SELECT 
    employee_id,
    employee_name,
    photo_url
FROM OHR_Employee_Agent_View
WHERE photo_url IS NOT NULL
LIMIT 5;
```

Debería mostrar URLs como:
```
https://onelake.dfs.fabric.microsoft.com/[workspace-id]/[lakehouse-id]/Files/employee_photos/102020.jpg
```

---

### **PASO 3: Actualizar Data Agent en Fabric**

1. Ve a tu workspace en Fabric
2. Abre **OHR Agent** (Data agent)
3. Click **Settings** → **Data sources**
4. **Remove** la fuente de datos actual (si solo apunta a una tabla vieja)
5. **Add** → Selecciona **`OHR_Employee_Agent_View`**
6. **Save**
7. Espera **5 minutos** para que se indexe

---

### **PASO 4: Configurar Topic en Copilot Studio**

Tu Topic debe tener esta estructura de nodos:

```
┌────────────────────────────────────────┐
│ 1. TRIGGER                             │
│    Phrases: "dame la foto de {Name}"   │
│             "muéstrame a {Name}"       │
│    Entity: Name (String)               │
└───────────┬─────────────────────────────┘
            │
┌───────────▼─────────────────────────────┐
│ 2. CREATE GENERATIVE ANSWERS           │
│    (Query Data Agent)                   │
│                                         │
│    Connection: OHR Agent                │
│    Data source: OHR_Employee_Agent_View │
│    Search term: Topic.Name              │
│                                         │
│    Output → Topic.DataResponse          │
└───────────┬─────────────────────────────┘
            │
┌───────────▼─────────────────────────────┐
│ 3. PARSE JSON                          │
│    (Extract employee data)              │
│                                         │
│    Set variable value:                  │
│                                         │
│    Topic.EmployeeID =                   │
│      Topic.DataResponse.                │
│      SearchQueryResult.value[0].        │
│      employee_id                        │
│                                         │
│    Topic.EmployeeName =                 │
│      Topic.DataResponse.                │
│      SearchQueryResult.value[0].        │
│      employee_name                      │
│                                         │
│    Topic.Position =                     │
│      Topic.DataResponse.                │
│      SearchQueryResult.value[0].        │
│      position                           │
│                                         │
│    Topic.Department =                   │
│      Topic.DataResponse.                │
│      SearchQueryResult.value[0].        │
│      department                         │
│                                         │
│    Topic.PhotoURL =                     │
│      Topic.DataResponse.                │
│      SearchQueryResult.value[0].        │
│      photo_url                          │
└───────────┬─────────────────────────────┘
            │
┌───────────▼─────────────────────────────┐
│ 4. SEND ADAPTIVE CARD                  │
│    (Show employee with photo)           │
│                                         │
│    Message type: Adaptive Card          │
│    [Pegar JSON abajo]                   │
└─────────────────────────────────────────┘
```

---

### **PASO 5: Copiar Adaptive Card Template**

En el nodo "Send a message", selecciona **Adaptive Card** y pega este JSON:

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
      "horizontalAlignment": "Center",
      "color": "Accent"
    },
    {
      "type": "ColumnSet",
      "separator": true,
      "spacing": "Medium",
      "columns": [
        {
          "type": "Column",
          "width": "auto",
          "items": [
            {
              "type": "Image",
              "url": "${Topic.PhotoURL}",
              "size": "Large",
              "style": "Person",
              "altText": "Photo of ${Topic.EmployeeName}"
            }
          ],
          "verticalContentAlignment": "Center"
        },
        {
          "type": "Column",
          "width": "stretch",
          "items": [
            {
              "type": "TextBlock",
              "text": "${Topic.EmployeeName}",
              "weight": "Bolder",
              "size": "ExtraLarge",
              "wrap": true
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
                  "title": "Department:",
                  "value": "${Topic.Department}"
                }
              ],
              "spacing": "Small"
            }
          ],
          "verticalContentAlignment": "Center"
        }
      ]
    }
  ],
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
```

**Importante**: Copilot Studio reemplazará automáticamente `${Topic.PhotoURL}`, `${Topic.EmployeeName}`, etc. con los valores reales de tus variables.

---

## 🧪 Testing

### **Test 1: Verificar Data Agent**

En el chat de prueba de Copilot Studio:

```
User: "dame la foto de Ricardo"
```

**Verificar en Variables del Topic**:
- `Topic.DataResponse` debe tener contenido (no vacío)
- `Topic.EmployeeID` debe tener valor (ej: "102020")
- `Topic.PhotoURL` debe tener URL completa OneLake

### **Test 2: Verificar Adaptive Card**

El chat debe mostrar:
- ✅ Tarjeta profesional con imagen renderizada
- ✅ Nombre del empleado en grande
- ✅ Información (ID, Puesto, Departamento)
- ✅ Botón "Generate PowerPoint"

**Si la imagen muestra icono roto** 🖼️❌:
- Verificar permisos del Data Agent en Lakehouse Files
- Abrir la URL `Topic.PhotoURL` en navegador para confirmar accesibilidad

---

## 📊 (Opcional) Generar PowerPoint con Azure OpenAI

### **Desplegar Azure Function**

```bash
# Crear proyecto
func init EmployeePPTGenerator --python
cd EmployeePPTGenerator

# Copiar el código de generate_ppt_with_openai.py

# Crear requirements.txt
echo "python-pptx==0.6.21
openai==1.12.0
Pillow==10.2.0
requests==2.31.0
azure-functions==1.18.0
azure-identity==1.15.0" > requirements.txt

# Desplegar
func azure functionapp publish employee-ppt-api --python
```

### **Configurar Topic para PowerPoint**

Agrega este nodo después del Adaptive Card:

```yaml
Nodo: On message activity
  Condition: 
    System.Activity.Value.action equals "generate_ppt"

  ↓
  
Nodo: HTTP Request
  Method: POST
  URL: https://employee-ppt-api.azurewebsites.net/api/generate_ppt
  
  Headers:
    Content-Type: application/json
    x-functions-key: [tu-function-key]
  
  Body:
    {
      "employees": [
        {
          "employee_id": "${Topic.EmployeeID}",
          "employee_name": "${Topic.EmployeeName}",
          "position": "${Topic.Position}",
          "department": "${Topic.Department}",
          "photo_url": "${Topic.PhotoURL}"
        }
      ],
      "presentation_title": "Employee Profile: ${Topic.EmployeeName}",
      "use_ai_description": true
    }
  
  Timeout: 30 seconds
  Output → Topic.PPTResponse

  ↓
  
Nodo: Message
  Text:
    "✅ PowerPoint generado!
    
    📥 Descarga: ${Topic.PPTResponse.download_url}
    📊 Diapositivas: ${Topic.PPTResponse.slide_count}
    💾 Tamaño: ${Topic.PPTResponse.file_size_mb} MB"
```

---

## 🐛 Troubleshooting

### **Problema 1: `Topic.DataResponse` está vacío**

**Causa**: Data Agent no encontró resultados

**Solución**:
```yaml
Después de "Create generative answers", agregar:

Nodo: Condition
  IF Topic.DataResponse.SearchQueryResult.value is empty
  THEN:
    Message: "❌ No encontré información para ese empleado. Verifica el nombre."
    End conversation
  ELSE:
    Continuar con Parse JSON
```

### **Problema 2: `Topic.PhotoURL` tiene valor pero imagen muestra icono roto**

**Causa**: Data Agent no tiene permisos para acceder a Lakehouse Files

**Solución**:
1. En Fabric, ve a tu **Lakehouse** → **Settings** → **Permissions**
2. Agregar **OHR Agent** (service principal del Data Agent) con rol **Contributor**
3. Esperar 5 minutos y probar de nuevo

**Verificar manualmente**:
- Copia el valor de `Topic.PhotoURL`
- Pégalo en navegador
- Si descarga la imagen → permisos OK
- Si error 403/404 → problema de permisos

### **Problema 3: Adaptive Card no se muestra, solo texto**

**Causa**: JSON del Adaptive Card tiene error de sintaxis

**Solución**:
- Copiar el JSON exacto del template en este documento
- NO modificar manualmente los `${...}` placeholders
- Copilot Studio los detecta automáticamente

**Validar JSON**:
- Usa [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- Pega tu JSON
- Reemplaza `${Topic.PhotoURL}` por una URL de prueba
- Si renderiza → JSON es válido

### **Problema 4: Variables `${Topic.EmployeeName}` se muestran literales**

**Causa**: Variables no están definidas en el scope del nodo

**Solución**:
- Verificar que el nodo "Parse JSON" esté **ANTES** del "Send Adaptive Card"
- Verificar ortografía exacta de variables
- Usar el editor Power Fx de Copilot Studio (debe mostrar autocomplete)

### **Problema 5: Notebook falla en `save_base64_to_lakehouse()`**

**Error**: `'trident.workspace.id' not found`

**Solución**:
```python
# Alternativa: Hardcodear IDs temporalmente para testing
workspace_id = "TU_WORKSPACE_ID"  # Cópialo de la URL de Fabric
lakehouse_id = "TU_LAKEHOUSE_ID"  # Lo ves en Settings del Lakehouse

# O usar mssparkutils para obtenerlos
workspace_id = mssparkutils.env.getWorkspaceId()
lakehouse_id = mssparkutils.notebook.lakehouse.getLakehouseId()
```

---

## ✅ Checklist de Implementación

### **Fase 1: Preparación de Datos**
- [ ] Abrir notebook "OHR Base64 Image Parser" en Fabric
- [ ] Agregar nueva celda con código `save_base64_to_lakehouse()`
- [ ] Ejecutar notebook completo
- [ ] Verificar archivos JPG en `Files/employee_photos/`
- [ ] Verificar tabla `OHR_Employee_Agent_View` creada
- [ ] Confirmar que columna `photo_url` tiene URLs OneLake

### **Fase 2: Configuración Data Agent**
- [ ] Abrir OHR Agent en Fabric
- [ ] Settings → Data sources → Add `OHR_Employee_Agent_View`
- [ ] Save y esperar 5 minutos
- [ ] Probar query manual en Data Agent

### **Fase 3: Copilot Studio Topic**
- [ ] Crear/modificar Topic "Datos Aldo"
- [ ] Agregar nodo "Create generative answers"
- [ ] Conectar a OHR Agent
- [ ] Agregar nodo "Parse JSON" (extraer variables)
- [ ] Agregar nodo "Send Adaptive Card"
- [ ] Copiar JSON template exacto
- [ ] Vincular variables `${Topic.PhotoURL}` etc.
- [ ] Save Topic

### **Fase 4: Testing**
- [ ] Test 1: "dame la foto de Ricardo" → Verificar `Topic.DataResponse`
- [ ] Test 2: Verificar `Topic.PhotoURL` tiene URL
- [ ] Test 3: Adaptive Card se muestra con imagen ✅
- [ ] Test 4: Información (nombre, ID, puesto) correcta
- [ ] Test 5: Si imagen rota, verificar permisos Lakehouse

### **Fase 5: PowerPoint (Opcional)**
- [ ] Desplegar `generate_ppt_with_openai.py` en Azure Functions
- [ ] Obtener Function Key
- [ ] Configurar variables de entorno (Azure OpenAI keys)
- [ ] Agregar nodo HTTP Request en Topic
- [ ] Probar botón "Generate PowerPoint"
- [ ] Verificar descarga de .pptx

---

## 📊 Resultado Final

**Antes** ❌:
```
User: "dame la foto de Aldo"
Bot: "<img src='data:image/png;base64,/9j/4AAQSkZJRg...' />"
     (Texto plano, no renderiza)
```

**Después** ✅:
```
User: "dame la foto de Aldo"
Bot: [Adaptive Card profesional]
     - Imagen de Aldo renderizada
     - Nombre: Ricardo Morion Perez
     - ID: 102020
     - Puesto: Manager Administration & Support
     - Botón: 📊 Generate PowerPoint
```

---

## 📞 Soporte

Si encuentras problemas:
1. Verificar cada paso del checklist
2. Revisar sección Troubleshooting arriba
3. Validar permisos de Data Agent en Lakehouse
4. Confirmar que URLs OneLake son accesibles desde navegador

---

**🎯 Con esta solución, tu agente OHR mostrará imágenes profesionalmente en Copilot Studio.** 🚀
