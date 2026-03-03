# 🎯 Configuración Completa del Topic para VW_TEST_DATABOT_ORIGINAL

**Problema**: El HTML `<img src='data:image/png;base64,...'>` se muestra como texto en Copilot Studio  
**Solución**: Usar Adaptive Cards + transformar datos a URLs HTTP

---

## 📊 **TU TABLA ACTUAL**

```sql
-- Tabla en Fabric
VW_TEST_DATABOT_ORIGINAL

Columnas:
- employee_id (string)
- employee_name (string)
- department (string)
- position (string)
- photo_url (string) -- ⚠️ Contiene: "data:image/png;base64,iVBORw0KGgo..."
```

---

## 🔧 **PASO 1: Preparar los Datos (CRÍTICO)**

### **Problema con tu columna `photo_url`**

❌ **Formato actual**: `data:image/png;base64,iVBORw0KGgoAAAANS...`  
❌ **Por qué no funciona**: Adaptive Cards **NO acepta data URIs**, solo URLs HTTP o HTTPS

### **Opción A: Transformar a URLs HTTP (RECOMENDADO)**

Ejecuta el notebook **[snowflake_to_fabric_notebook.py](./snowflake_to_fabric_notebook.py)**:

```python
# Este notebook:
# 1. Lee VW_TEST_DATABOT_ORIGINAL
# 2. Extrae el base64 de photo_url
# 3. Guarda imágenes como archivos .jpg en Lakehouse Files
# 4. Crea nueva tabla: employee_agent_view con URLs OneLake
```

**Resultado**: Nueva tabla con URLs HTTP funcionales

```sql
employee_agent_view

Columnas:
- employee_id (string)
- employee_name (string)
- department (string)
- position (string)
- photo_url (string) -- ✅ "https://onelake.dfs.fabric.microsoft.com/.../aldo.jpg"
- thumbnail_base64 (string) -- Para vistas previas pequeñas
```

### **Opción B: Usar API para convertir base64 → HTTP (Rápido)**

1. Despliega **[fabric_image_api.py](./fabric_image_api.py)** en Azure Container Apps
2. La API convierte base64 a URLs HTTP en tiempo real
3. No necesitas modificar tu tabla

```bash
# Deploy rápido
cd fabric_image_api
az containerapp up --name fabric-image-api --resource-group rg-copilot --source .
```

**URL resultante**: `https://fabric-image-api.azurecontainerapps.io/image/base64?data=...`

---

## 🤖 **PASO 2: Configurar el Topic en Copilot Studio**

### **Arquitectura del Topic**

```
┌─────────────────────────────────────────────┐
│ 1. TRIGGER                                  │
│    Phrase: "dame la imagen de {EmployeeName}"│
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 2. SEND ACTIVITY TO DATA AGENT              │
│    (Create generative answers)               │
│                                              │
│    Connection: [Tu Fabric Data Agent]        │
│    Data source: VW_TEST_DATABOT_ORIGINAL     │
│    Search term: Topic.EmployeeName           │
│    Output variable: Topic.AgentActivity      │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 3. PARSE DATA AGENT RESPONSE                │
│    (Parse JSON - Set variable value)         │
│                                              │
│    Parse: Topic.AgentActivity.               │
│           SearchQueryResult.value[0]         │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 4. CONVERT BASE64 TO HTTP URL               │
│    (Condition + HTTP Request)                │
│                                              │
│    IF photo_url starts with "data:image"     │
│    THEN call API to convert                  │
│    ELSE use URL directly                     │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 5. SHOW ADAPTIVE CARD                       │
│    (Send message - Adaptive Card)            │
│                                              │
│    Card: [Ver código abajo]                  │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│ 6. (OPCIONAL) GENERATE POWERPOINT           │
│    (HTTP Request to Azure Function)          │
└──────────────────────────────────────────────┘
```

---

## 🔨 **CONFIGURACIÓN NODO POR NODO**

### **Nodo 1: Trigger**

```yaml
Tipo: Trigger phrases
Frases de ejemplo:
  - "muéstrame la foto de {EmployeeName}"
  - "dame la imagen de {EmployeeName}"
  - "busca a {EmployeeName}"
  
Entidades:
  - EmployeeName (tipo: String)
```

---

### **Nodo 2: Create Generative Answers (Data Agent)**

```yaml
Tipo: Create generative answers
Nombre: QueryFabricDataAgent

Configuración:
  Connection: [Selecciona tu Fabric Data Agent]
  
  Data sources:
    ✅ VW_TEST_DATABOT_ORIGINAL
  
  Input:
    Search term: System.Activity.Text
    # O específicamente: Topic.EmployeeName
  
  Properties:
    Content moderation: Moderate
    AI model: Default
    
  Output variables:
    → Activity: Topic.AgentActivity
```

**⚠️ IMPORTANTE**: Este nodo devuelve respuesta generativa en lenguaje natural. Para obtener los datos estructurados, necesitas el siguiente paso.

---

### **Nodo 3: Parse JSON Response**

El Data Agent devuelve JSON en `Topic.AgentActivity.SearchQueryResult`. Necesitas extraer los campos.

#### **Opción 3A: Con "Parse JSON" (Recomendado)**

```yaml
Tipo: Parse value
Nombre: ExtractEmployeeData

Parse value from:
  Topic.AgentActivity.SearchQueryResult

Schema: (Auto-detect o usar este)
{
  "type": "object",
  "properties": {
    "value": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "employee_id": {"type": "string"},
          "employee_name": {"type": "string"},
          "department": {"type": "string"},
          "position": {"type": "string"},
          "photo_url": {"type": "string"}
        }
      }
    }
  }
}

Output variables:
  → Topic.EmployeeData (object)
```

#### **Opción 3B: Con "Set variable value" (Manual)**

```yaml
Tipo: Set variable value
Asignaciones múltiples:

Variable: Topic.EmployeeID
To value: Topic.AgentActivity.SearchQueryResult.value[0].employee_id

Variable: Topic.EmployeeName  
To value: Topic.AgentActivity.SearchQueryResult.value[0].employee_name

Variable: Topic.Department
To value: Topic.AgentActivity.SearchQueryResult.value[0].department

Variable: Topic.Position
To value: Topic.AgentActivity.SearchQueryResult.value[0].position

Variable: Topic.PhotoURL
To value: Topic.AgentActivity.SearchQueryResult.value[0].photo_url
```

---

### **Nodo 4: Convert Base64 to HTTP URL**

Tu `photo_url` tiene formato `data:image/png;base64,...` que **NO funciona** en Adaptive Cards.

#### **Sub-nodo 4A: Condición**

```yaml
Tipo: Add a condition
Nombre: CheckPhotoFormat

Condition:
  Topic.PhotoURL
  starts with
  "data:image"
```

#### **Sub-nodo 4B: Call Image API (si es base64)**

```yaml
Tipo: Send HTTP request
Nombre: ConvertBase64ToHTTP

Ruta TRUE de la condición:

Request:
  Method: POST
  URL: https://fabric-image-api.azurecontainerapps.io/image/base64
  
  Headers:
    Content-Type: application/json
  
  Body:
    {
      "base64_data": "${Topic.PhotoURL}",
      "employee_id": "${Topic.EmployeeID}"
    }

Response:
  Parse as: JSON
  Output → Topic.ImageAPIResponse
  
Extract:
  Topic.HTTPImageURL = Topic.ImageAPIResponse.image_url
```

#### **Sub-nodo 4C: Usar URL directamente (si ya es HTTP)**

```yaml
Tipo: Set variable value
Nombre: UseDirectURL

Ruta FALSE de la condición:

Variable: Topic.HTTPImageURL
To value: Topic.PhotoURL
```

---

### **Nodo 5: Show Adaptive Card**

```yaml
Tipo: Send a message
Message type: Adaptive Card
Nombre: ShowEmployeeCard
```

**📋 COPIAR Y PEGAR ESTE JSON:**

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "Perfil del Empleado",
      "weight": "Bolder",
      "size": "Large",
      "horizontalAlignment": "Center"
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
              "url": "${Topic.HTTPImageURL}",
              "size": "Large",
              "style": "Person",
              "altText": "Foto de ${Topic.EmployeeName}"
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
                  "title": "Puesto:",
                  "value": "${Topic.Position}"
                },
                {
                  "title": "Departamento:",
                  "value": "${Topic.Department}"
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
          "title": "Generar PowerPoint",
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

**🔗 Reemplazar variables dinámicamente**:

En Copilot Studio, cuando pegas el JSON, automáticamente detectará `${Topic.HTTPImageURL}` y lo vinculará a tus variables del Topic.

---

### **Nodo 6: Generate PowerPoint (Opcional)**

Este nodo se activa cuando el usuario presiona el botón "Generar PowerPoint" en la Adaptive Card.

#### **Trigger del botón**

```yaml
Tipo: On message received
Condition:
  System.Activity.Text
  equals
  "generate_ppt"
  
  # O detectar el submit de la Adaptive Card:
  System.Activity.Value.action
  equals
  "generate_ppt"
```

#### **HTTP Request a Azure Function**

```yaml
Tipo: Send HTTP request
Nombre: GeneratePowerPoint

Request:
  Method: POST
  URL: https://[tu-function-app].azurewebsites.net/api/generate_ppt
  
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
          "photo_url": "${Topic.HTTPImageURL}"
        }
      ],
      "presentation_title": "Perfil de ${Topic.EmployeeName}",
      "use_ai_description": true
    }
  
  Timeout: 30 seconds

Response:
  Parse as: JSON
  Output → Topic.PPTResponse
```

#### **Mostrar resultado**

```yaml
Tipo: Send a message
Nombre: SendPPTLink

Message:
  "✅ PowerPoint generado exitosamente!
  
  📥 Descarga aquí: ${Topic.PPTResponse.download_url}
  
  📊 Detalles:
  - Diapositivas: ${Topic.PPTResponse.slide_count}
  - Tamaño: ${Topic.PPTResponse.file_size_mb} MB"
```

---

## ⚡ **CONFIGURACIÓN RÁPIDA (Sin API - Solo para URLs HTTP)**

Si ya transformaste `photo_url` a URLs HTTP usando el notebook, tu Topic puede ser **MÁS SIMPLE**:

```
1. Trigger
   ↓
2. Create generative answers (Fabric Data Agent)
   ↓
3. Parse JSON
   ↓
4. Show Adaptive Card (usando Topic.PhotoURL directamente)
```

**JSON simplificado:**

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "Image",
      "url": "${Topic.PhotoURL}",
      "size": "Large"
    },
    {
      "type": "TextBlock",
      "text": "${Topic.EmployeeName}",
      "weight": "Bolder",
      "size": "Large"
    }
  ]
}
```

---

## 🧪 **TESTING**

### **Test 1: Verificar Data Agent**

```
Usuario: "muéstrame a Aldo"

Verificar:
✅ Topic.AgentActivity tiene datos
✅ Topic.EmployeeID = "ALDO" (o similar)
✅ Topic.PhotoURL tiene valor
```

### **Test 2: Verificar conversión de imagen**

```
Si photo_url = "data:image/png;base64,iVBORw0..."

Verificar:
✅ Condición detecta "data:image" → TRUE
✅ HTTP Request se ejecuta
✅ Topic.HTTPImageURL = "https://fabric-image-api.../image/..."
```

### **Test 3: Verificar Adaptive Card**

```
Verificar en el chat:
✅ Se muestra una tarjeta con imagen
✅ La imagen es visible (no broken)
✅ Textos (nombre, puesto, etc.) correctos
✅ Botón "Generar PowerPoint" funciona
```

### **Test 4: Verificar PowerPoint**

```
Click en "Generar PowerPoint"

Verificar:
✅ Request a Azure Function completa
✅ Response tiene download_url
✅ Link funciona y descarga .pptx
✅ PowerPoint contiene foto y datos
```

---

## 🐛 **TROUBLESHOOTING**

### **Problema 1: Image no se muestra en Adaptive Card**

```
Síntoma: Icono de imagen rota 🖼️❌

Causas posibles:
❌ photo_url tiene formato "data:image/..." (no soportado)
❌ URL HTTP no es accesible públicamente
❌ Falta CORS en la API

Solución:
✅ Verificar que Topic.HTTPImageURL sea HTTP/HTTPS
✅ Abrir URL en navegador para verificar accesibilidad
✅ Configurar CORS en fabric_image_api.py:
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://*.powervirtualagents.com"],
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["*"]
   )
```

### **Problema 2: Data Agent no devuelve resultados**

```
Síntoma: Topic.AgentActivity está vacío

Causas:
❌ Búsqueda no encuentra coincidencias
❌ Tabla VW_TEST_DATABOT_ORIGINAL no indexada
❌ Permisos insuficientes

Solución:
✅ Verificar en Fabric que la vista existe
✅ Ejecutar query manual: SELECT * FROM VW_TEST_DATABOT_ORIGINAL WHERE employee_name LIKE '%Aldo%'
✅ Dar permisos al Data Agent sobre la vista
```

### **Problema 3: Topic se queda "In Progress"**

```
Síntoma: Chat muestra spinner infinito

Causas:
❌ HTTP Request sin timeout
❌ Nodo "Create generative answers" sin fallback
❌ Error en parsing de JSON

Solución:
✅ Agregar timeout a HTTP Requests (30 segundos)
✅ Agregar condiciones para verificar responses vacías:
   IF Topic.AgentActivity is empty
   THEN Message: "No encontré resultados para ese empleado"
```

### **Problema 4: Variables no se reemplazan en Adaptive Card**

```
Síntoma: Se muestra literal "${Topic.EmployeeName}" en la tarjeta

Causa:
❌ Variable no definida en el scope del Topic

Solución:
✅ Verificar ortografía exacta de variables
✅ Usar Power Fx expression editor para confirmar variables disponibles
✅ Si no aparece en autocomplete, la variable no existe
```

### **Problema 5: PowerPoint sin imágenes**

```
Síntoma: PPT se genera pero las fotos no aparecen

Causa:
❌ generate_ppt_with_openai.py no puede descargar la URL

Solución:
✅ Verificar que photo_url sea accesible sin autenticación
✅ Para OneLake URLs, usar Managed Identity:
   # En generate_ppt_with_openai.py
   from azure.identity import DefaultAzureCredential
   credential = DefaultAzureCredential()
```

---

## 📚 **REFERENCIAS**

- **[GUIA_COPILOT_STUDIO_INTEGRATION.md](./GUIA_COPILOT_STUDIO_INTEGRATION.md)** - Guía completa de implementación
- **[COPILOT_STUDIO_EXAMPLES.md](./COPILOT_STUDIO_EXAMPLES.md)** - Más ejemplos de Topics
- **[snowflake_to_fabric_notebook.py](./snowflake_to_fabric_notebook.py)** - Transformar datos de Snowflake
- **[fabric_image_api.py](./fabric_image_api.py)** - API para servir imágenes
- **[generate_ppt_with_openai.py](./generate_ppt_with_openai.py)** - Generador de PowerPoint
- **[adaptive_card_employee_template.json](./adaptive_card_employee_template.json)** - Template básico

---

## 🎯 **CHECKLIST DE IMPLEMENTACIÓN**

### **Preparación de Datos**
- [ ] Ejecutar `snowflake_to_fabric_notebook.py` para crear `employee_agent_view`
- [ ] O desplegar `fabric_image_api.py` en Azure Container Apps
- [ ] Verificar que las imágenes sean accesibles vía HTTP

### **Configuración del Topic**
- [ ] Crear Trigger con frases de ejemplo
- [ ] Agregar nodo "Create generative answers" conectado a Fabric Data Agent
- [ ] Configurar parsing de JSON response
- [ ] Agregar conversión base64 → HTTP (si aplica)
- [ ] Pegar y configurar Adaptive Card JSON
- [ ] Vincular variables del Topic a placeholders `${...}`

### **Configuración de PowerPoint (Opcional)**
- [ ] Desplegar `generate_ppt_with_openai.py` en Azure Functions
- [ ] Obtener Function Key
- [ ] Configurar HTTP Request en Topic
- [ ] Agregar botón "Generar PowerPoint" en Adaptive Card

### **Testing**
- [ ] Test básico: Buscar empleado por nombre
- [ ] Test visual: Verificar que imagen se muestre
- [ ] Test PowerPoint: Generar y descargar presentación
- [ ] Test error handling: Buscar empleado inexistente
- [ ] Test rendimiento: Múltiples consultas seguidas

### **Producción**
- [ ] Publicar Topic en Copilot Studio
- [ ] Configurar canales (Teams, Web Chat, etc.)
- [ ] Monitorear Analytics de uso
- [ ] Revisar logs de errores

---

## 💡 **PRÓXIMOS PASOS RECOMENDADOS**

1. **Ahora mismo**: Ejecuta [snowflake_to_fabric_notebook.py](./snowflake_to_fabric_notebook.py) para transformar tus datos
2. **Después**: Copia el JSON de Adaptive Card en tu Topic
3. **Probar**: Testea con "dame la imagen de Aldo"
4. **Opcional**: Despliega la Azure Function para PowerPoint

---

**¿Necesitas ayuda con algún paso específico?** 🚀
