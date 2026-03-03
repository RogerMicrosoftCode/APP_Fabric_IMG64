# 🤖 Guía Completa: Mostrar Imágenes en Fabric Data Agent y Generar PowerPoint

## 📋 Problema Identificado

Tu **Fabric Data Agent** devuelve las fotos como **texto base64** en lugar de mostrar las imágenes. Copilot Studio **no puede renderizar HTML** directamente, por eso no funciona la fórmula `$"<img src='data:image/png;base64,...'>"`.

**Solución implementada:**
1. ✅ Almacenar fotos en **Fabric Lakehouse Files** (no base64 en tablas)
2. ✅ Crear **API REST** que sirva las imágenes como URLs HTTP
3. ✅ Usar **Adaptive Cards** en Copilot Studio para mostrar imágenes
4. ✅ Generar **PowerPoint automático** con Azure OpenAI/Foundry

---

## 🏗️ Arquitectura de la Solución

```
┌─────────────────────────────────────────────────────────────────┐
│  PASO 1: MIGRACIÓN DE DATOS                                     │
│  ┌──────────────┐      ┌──────────────────┐      ┌───────────┐ │
│  │  Snowflake   │─────▶│ Fabric Notebook  │─────▶│ Lakehouse │ │
│  │  (base64)    │      │  (Procesamiento) │      │  Files    │ │
│  └──────────────┘      └──────────────────┘      └───────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PASO 2: SERVICIO DE IMÁGENES                                   │
│  ┌──────────────┐      ┌──────────────────┐      ┌───────────┐ │
│  │  Lakehouse   │─────▶│  FastAPI         │─────▶│  HTTPS    │ │
│  │  Files       │      │  (Image Service) │      │  URLs     │ │
│  └──────────────┘      └──────────────────┘      └───────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PASO 3: COPILOT STUDIO INTEGRATION                             │
│  ┌──────────────┐      ┌──────────────────┐      ┌───────────┐ │
│  │ Data Agent   │─────▶│ Adaptive Card    │─────▶│  Usuario  │ │
│  │ (Query SQL)  │      │ (Muestra imagen) │      │  ve foto  │ │
│  └──────────────┘      └──────────────────┘      └───────────┘ │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PASO 4: GENERACIÓN DE POWERPOINT                               │
│  ┌──────────────┐      ┌──────────────────┐      ┌───────────┐ │
│  │ Copilot      │─────▶│ Azure OpenAI +   │─────▶│ .pptx     │ │
│  │ Agent Query  │      │ python-pptx      │      │ con fotos │ │
│  └──────────────┘      └──────────────────┘      └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 PASO 1: Migrar Datos de Snowflake a Fabric Lakehouse

### 1.1 Ejecutar Notebook en Fabric

Usa el archivo: **`snowflake_to_fabric_notebook.py`**

**Celdas a ejecutar:**

```python
# CELDA 1: Instalar dependencias
%pip install snowflake-connector-python Pillow==10.2.0

# CELDA 2-8: Copiar todo el código del archivo
# El notebook hace:
# ✅ Conecta a Snowflake
# ✅ Lee fotos en base64
# ✅ Convierte a imágenes .jpg
# ✅ Guarda en Lakehouse Files (no en tablas Delta)
# ✅ Crea tabla "employee_agent_view" con URLs de OneLake
```

### 1.2 Verificar Resultados

Después de ejecutar, deberías tener:

```sql
SELECT * FROM employee_agent_view LIMIT 5;

-- Columnas:
-- employee_id
-- employee_name
-- department
-- position
-- photo_url         ← URL de OneLake (https://...)
-- thumbnail_base64  ← Para previews
-- employee_description
```

**✅ CHECKPOINT**: Las fotos ahora están en **Lakehouse Files**, no como base64 en tablas.

---

## 🌐 PASO 2: Desplegar API de Imágenes

### 2.1 Desplegar FastAPI en Azure Container Apps

Usa el archivo: **`fabric_image_api.py`**

**Opción A: Azure Container Apps (Recomendado)**

```bash
# 1. Crear Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY fabric_image_api.py .
RUN pip install fastapi uvicorn pillow requests azure-identity azure-storage-blob

EXPOSE 8000
CMD ["uvicorn", "fabric_image_api:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# 2. Build y push a Azure Container Registry
az acr build --registry YOUR_ACR --image fabric-image-api:latest .

# 3. Desplegar en Container Apps
az containerapp create \
  --name fabric-image-api \
  --resource-group YOUR_RG \
  --environment YOUR_ENV \
  --image YOUR_ACR.azurecr.io/fabric-image-api:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --env-vars \
    FABRIC_WORKSPACE_ID=your-workspace-id \
    FABRIC_LAKEHOUSE_ID=your-lakehouse-id
```

**Opción B: Azure Functions (Alternativa)**

```bash
func init ImageServiceFunction --python
# Copiar código de fabric_image_api.py adaptado a HttpTrigger
func azure functionapp publish YOUR_FUNCTION_APP
```

### 2.2 Probar API

```bash
# Health check
curl https://YOUR_API.azurecontainerapps.io/

# Servir imagen desde OneLake
curl https://YOUR_API.azurecontainerapps.io/image/onelake/12345

# Generar Adaptive Card
curl "https://YOUR_API.azurecontainerapps.io/adaptive-card/employee?employee_id=12345&employee_name=Pamela%20Yissell&department=HR&position=Manager&api_base_url=https://YOUR_API.azurecontainerapps.io"
```

**✅ CHECKPOINT**: La API responde correctamente y sirve imágenes.

---

## 🤖 PASO 3: Configurar Copilot Studio para Mostrar Imágenes

### 3.1 Configurar Fabric Data Agent Connection

En **Copilot Studio** → **Settings** → **Connections**:

1. Selecciona tu **Fabric Data Agent** existente
2. Asegúrate que apunta a la tabla: `employee_agent_view`
3. Guardar

### 3.2 Crear Topic con Adaptive Cards

**En Copilot Studio:**

1. Ir a **Topics** → **+ New topic** → "Mostrar Perfil de Empleado"

2. **Trigger phrases:**
   - "muéstrame el perfil de [nombre]"
   - "quiero ver la foto de [nombre]"
   - "busca información de [empleado]"

3. **Question node:**
   ```
   Variable: employeeName
   Question: "¿De qué empleado quieres ver el perfil?"
   ```

4. **Data Agent Query node:**
   ```
   Action: Query Fabric Data Agent
   
   Query natural language:
   "Busca el empleado con nombre {employeeName} en la tabla employee_agent_view"
   
   Parse response to variables:
   - employee_id
   - employee_name
   - department
   - position
   - photo_url
   ```

5. **HTTP Request node (Generar Adaptive Card):**
   ```
   Method: GET
   URL: https://YOUR_API.azurecontainerapps.io/adaptive-card/employee
   
   Query parameters:
   - employee_id = {employee_id}
   - employee_name = {employee_name}
   - department = {department}
   - position = {position}
   - api_base_url = https://YOUR_API.azurecontainerapps.io
   
   Save response as: adaptiveCardJson
   ```

6. **Message node (Mostrar Adaptive Card):**
   ```
   Type: Adaptive Card
   Card JSON: {adaptiveCardJson}
   ```

### 3.3 Ejemplo de Adaptive Card Resultante

La API retorna este JSON (se renderiza automáticamente):

```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "ColumnSet",
      "columns": [
        {
          "type": "Column",
          "items": [
            {
              "type": "Image",
              "url": "https://YOUR_API.azurecontainerapps.io/image/onelake/12345",
              "size": "Medium",
              "style": "Person"
            }
          ]
        },
        {
          "type": "Column",
          "items": [
            {"type": "TextBlock", "text": "Pamela Yissell", "weight": "Bolder"},
            {"type": "TextBlock", "text": "Senior HR Manager"},
            {"type": "TextBlock", "text": "📍 Human Resources"}
          ]
        }
      ]
    }
  ]
}
```

**✅ CHECKPOINT**: El agente ahora muestra la imagen correctamente en Adaptive Card.

---

## 📊 PASO 4: Generar PowerPoint con Azure OpenAI

### 4.1 Desplegar Servicio de Generación PPT

Usa el archivo: **`generate_ppt_with_openai.py`**

**Desplegar como Azure Function:**

```bash
# 1. Crear Function App
func init PPTGeneratorFunction --python
cd PPTGeneratorFunction

# 2. Crear HttpTrigger
func new --name GeneratePPT --template "HTTP trigger"

# 3. Copiar código de generate_ppt_with_openai.py al __init__.py

# 4. Instalar dependencias (requirements.txt)
cat > requirements.txt << 'EOF'
azure-functions
python-pptx
openai
pillow
requests
azure-identity
EOF

# 5. Desplegar
func azure functionapp publish YOUR_FUNCTION_APP
```

**Configurar variables de entorno:**

```bash
az functionapp config appsettings set \
  --name YOUR_FUNCTION_APP \
  --resource-group YOUR_RG \
  --settings \
    AZURE_OPENAI_ENDPOINT="https://your-openai.openai.azure.com/" \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    FABRIC_API_ENDPOINT="https://YOUR_API.azurecontainerapps.io"
```

### 4.2 Crear Topic en Copilot Studio para Generar PPT

**Topic: "Generar Presentación de Empleados"**

1. **Trigger:**
   - "genera un powerpoint con los perfiles"
   - "crea una presentación con las fotos"

2. **Question node:**
   ```
   Variable: searchCriteria
   Question: "¿Qué empleados quieres incluir? (ej: departamento de HR)"
   ```

3. **Data Agent Query:**
   ```
   Query: "Busca todos los empleados de {searchCriteria} en employee_agent_view"
   
   Parse response to list: employeesList
   ```

4. **HTTP Request (Generar PPT):**
   ```
   Method: POST
   URL: https://YOUR_FUNCTION_APP.azurewebsites.net/api/GeneratePPT
   
   Headers:
   - Content-Type: application/json
   
   Body:
   {
       "employees": {employeesList},
       "title": "Perfiles de Empleados",
       "subtitle": "Generado automáticamente",
       "use_ai_descriptions": true
   }
   
   Save response as: pptDownloadUrl
   ```

5. **Message node:**
   ```
   "✅ He generado tu presentación con {employeesList.length} perfiles.
   
   Descárgala aquí: {pptDownloadUrl}"
   ```

### 4.3 Probar Generación de PPT

**Desde el agente:**

```
Usuario: "genera un powerpoint con Pamela Yissell"

Agente: 
✅ He generado tu presentación con 1 perfil.
📥 Descárgala aquí: https://storage.blob.core.windows.net/ppts/perfiles_123.pptx
```

**El PowerPoint incluirá:**
- ✅ Foto del empleado (descargada desde la API)
- ✅ Nombre, departamento, posición
- ✅ Descripción generada con Azure OpenAI
- ✅ Diseño profesional

**✅ CHECKPOINT**: PowerPoint se genera correctamente con todas las fotos.

---

## 🔧 Solución al Problema Específico del Topic

**En tu captura, viste:**
```
Set variable value: Var1 = $"<img src='data:image/png;base64,{Topic.Base64Aldo}'>"
```

**❌ PROBLEMA**: Copilot Studio no renderiza HTML.

**✅ SOLUCIÓN**:

1. **Elimina ese nodo** de "Set variable value"

2. **Reemplázalo con HTTP Request**:
   ```
   URL: https://YOUR_API.azurecontainerapps.io/image/base64
   Method: GET
   Query params:
   - data = {Topic.Base64Aldo}
   - format = jpeg
   - max_width = 300
   
   Save response as: imageUrl
   ```

3. **Usa Adaptive Card en lugar de HTML**:
   ```json
   {
     "type": "AdaptiveCard",
     "version": "1.5",
     "body": [
       {
         "type": "Image",
         "url": "{imageUrl}",
         "size": "Large"
       }
     ]
   }
   ```

---

## 📝 Checklist de Implementación

### Fase 1: Datos
- [ ] ✅ Ejecutar notebook `snowflake_to_fabric_notebook.py`
- [ ] ✅ Verificar tabla `employee_agent_view` creada
- [ ] ✅ Confirmar fotos guardadas en Lakehouse Files

### Fase 2: API
- [ ] ✅ Desplegar `fabric_image_api.py` en Azure Container Apps
- [ ] ✅ Probar endpoint `/image/onelake/{employee_id}`
- [ ] ✅ Probar endpoint `/adaptive-card/employee`

### Fase 3: Copilot Studio
- [ ] ✅ Configurar conexión a Fabric Data Agent
- [ ] ✅ Crear Topic "Mostrar Perfil de Empleado"
- [ ] ✅ Probar que la Adaptive Card muestra la imagen

### Fase 4: PowerPoint
- [ ] ✅ Desplegar `generate_ppt_with_openai.py` como Azure Function
- [ ] ✅ Configurar Azure OpenAI endpoint
- [ ] ✅ Crear Topic "Generar Presentación"
- [ ] ✅ Probar generación de PPT end-to-end

---

## 🐛 Troubleshooting

### Problema: "El agente no muestra la imagen"

**Solución:**
1. Verifica que la URL de la imagen es accesible públicamente
2. Prueba la URL directamente en el navegador
3. Verifica CORS en la API (debe permitir Copilot Studio)

### Problema: "Topic se queda 'In Progress'"

**Solución:**
1. Revisa los logs del Topic en Test pane
2. Asegúrate que el HTTP Request tiene timeout configurado (30s)
3. Verifica que la API responde en <10s

### Problema: "PowerPoint sin fotos"

**Solución:**
1. Verifica que `photo_url` en la tabla es válida
2. Prueba descargar manualmente con `requests.get(photo_url)`
3. Revisa logs de Azure Function para ver errores

---

## 📚 Archivos en el Repositorio

| Archivo | Propósito |
|---------|-----------|
| `snowflake_to_fabric_notebook.py` | Migra datos de Snowflake a Fabric Lakehouse |
| `fabric_image_api.py` | API FastAPI para servir imágenes como URLs HTTP |
| `adaptive_card_employee_template.json` | Template de Adaptive Card para Copilot Studio |
| `generate_ppt_with_openai.py` | Genera PowerPoint con Azure OpenAI + python-pptx |

---

## 🎯 Resultado Final

Después de implementar esta guía:

1. ✅ **Data Agent muestra imágenes** usando Adaptive Cards
2. ✅ **Topics no se quedan "In Progress"** con el nuevo enfoque
3. ✅ **PowerPoint se genera automáticamente** con fotos y descripciones IA
4. ✅ **Escalable** para 1,000+ empleados sin cambios

**¡Tu agente ahora puede mostrar fotos profesionalmente! 🚀**
