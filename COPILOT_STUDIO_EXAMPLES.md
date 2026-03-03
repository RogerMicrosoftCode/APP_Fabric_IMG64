# Ejemplos de Configuración - Copilot Studio Topics

Este archivo contiene ejemplos completos de configuración para Copilot Studio Topics que resuelven el problema de mostrar imágenes.

---

## 📋 Ejemplo 1: Topic Simple - "Buscar Empleado con Foto"

### Configuración del Topic

**Name:** `BuscarEmpleadoConFoto`

**Trigger Phrases:**
```
- busca a {employeeName}
- muéstrame a {employeeName}
- quiero ver la foto de {employeeName}
- información de {employeeName}
- perfil de {employeeName}
```

### Nodos del Topic

#### Nodo 1: Question (si no se capturó en trigger)
```yaml
Type: Question
Variable: employeeName
Question: "¿De qué empleado quieres ver el perfil?"
Save response as: Var_EmployeeName
```

#### Nodo 2: Data Agent Query
```yaml
Type: Call an action
Action: Query Fabric Data Agent

Configuration:
  Input:
    Natural Language Query: "Busca el empleado llamado {Var_EmployeeName} en la tabla employee_agent_view"
  
  Output (Parse to variables):
    - employee_id → Var_EmpID
    - employee_name → Var_EmpName  
    - department → Var_Department
    - position → Var_Position
    - photo_url → Var_PhotoURL
```

#### Nodo 3: Condition (Verificar si encontró empleado)
```yaml
Type: Condition

Condition: Var_EmpID is not blank

If TRUE → Go to Nodo 4
If FALSE → Go to Message "No encontré ese empleado"
```

#### Nodo 4: HTTP Request (Generar Adaptive Card)
```yaml
Type: Call an action
Action: HTTP Request

Configuration:
  Method: GET
  URL: https://YOUR_API.azurecontainerapps.io/adaptive-card/employee
  
  Query Parameters:
    - employee_id: {Var_EmpID}
    - employee_name: {Var_EmpName}
    - department: {Var_Department}
    - position: {Var_Position}
    - api_base_url: https://YOUR_API.azurecontainerapps.io
  
  Headers:
    - Content-Type: application/json
  
  Save response as: Var_AdaptiveCardJSON
```

#### Nodo 5: Message (Mostrar Adaptive Card)
```yaml
Type: Message

Content Type: Adaptive Card

Card JSON: {Var_AdaptiveCardJSON}
```

#### Nodo 6: Question (¿Quieres más información?)
```yaml
Type: Question
Variable: moreInfo
Question: "¿Quieres buscar a otro empleado?"

Options:
  - Sí → Go back to Nodo 1
  - No → End conversation
```

---

## 📊 Ejemplo 2: Topic Avanzado - "Generar PowerPoint con Perfiles"

### Configuración del Topic

**Name:** `GenerarPowerPointPerfiles`

**Trigger Phrases:**
```
- genera un powerpoint
- crea una presentación
- quiero un ppt con perfiles
- hazme una presentación de empleados
```

### Nodos del Topic

#### Nodo 1: Message (Explicación)
```yaml
Type: Message
Text: "Voy a crear una presentación de PowerPoint con los perfiles que me indiques. 📊"
```

#### Nodo 2: Question (Criterio de búsqueda)
```yaml
Type: Question
Variable: searchCriteria
Question: "¿Qué empleados quieres incluir? (Por ejemplo: 'departamento de HR', 'todos los managers', 'Pamela Yissell')"
Save response as: Var_SearchCriteria
```

#### Nodo 3: Data Agent Query
```yaml
Type: Call an action
Action: Query Fabric Data Agent

Configuration:
  Input:
    Natural Language Query: "Busca empleados que coincidan con: {Var_SearchCriteria} en la tabla employee_agent_view. Retorna employee_id, employee_name, department, position, photo_url"
  
  Output:
    Save entire response as: Var_EmployeesJSON
```

#### Nodo 4: Parse JSON Response
```yaml
Type: Parse value

Parse: Var_EmployeesJSON
Schema:
  employees: array
    - employee_id: string
    - employee_name: string
    - department: string
    - position: string
    - photo_url: string

Save as: Var_EmployeesList
```

#### Nodo 5: Condition (Verificar cantidad)
```yaml
Type: Condition

Condition: length(Var_EmployeesList) > 0

If TRUE → Go to Nodo 6
If FALSE → Message "No encontré empleados con ese criterio"
```

#### Nodo 6: Message (Confirmación)
```yaml
Type: Message
Text: "Encontré {length(Var_EmployeesList)} empleado(s). Generando presentación... ⏳"
```

#### Nodo 7: HTTP Request (Generar PPT)
```yaml
Type: Call an action
Action: HTTP Request

Configuration:
  Method: POST
  URL: https://YOUR_FUNCTION_APP.azurewebsites.net/api/GeneratePPT
  
  Headers:
    - Content-Type: application/json
  
  Body (JSON):
    {
      "employees": {Var_EmployeesList},
      "title": "Perfiles de Empleados",
      "subtitle": "Generado el {formatDateTime(utcNow(), 'dd/MM/yyyy')}",
      "use_ai_descriptions": true
    }
  
  Timeout: 60 seconds
  
  Save response as: Var_PPTResponse
```

#### Nodo 8: Parse PPT Response
```yaml
Type: Parse value

Parse: Var_PPTResponse
Schema:
  download_url: string
  file_name: string
  employee_count: number

Save as variables:
  - Var_DownloadURL
  - Var_FileName
  - Var_EmpCount
```

#### Nodo 9: Message (Entregar resultado)
```yaml
Type: Message with Adaptive Card

Card JSON:
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "TextBlock",
      "text": "✅ Presentación Generada",
      "weight": "Bolder",
      "size": "Large"
    },
    {
      "type": "TextBlock",
      "text": "Tu presentación con {Var_EmpCount} perfil(es) está lista.",
      "wrap": true,
      "spacing": "Medium"
    },
    {
      "type": "FactSet",
      "facts": [
        {
          "title": "Archivo:",
          "value": "{Var_FileName}"
        },
        {
          "title": "Perfiles incluidos:",
          "value": "{Var_EmpCount}"
        }
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "📥 Descargar PowerPoint",
      "url": "{Var_DownloadURL}"
    }
  ]
}
```

---

## 🔧 Ejemplo 3: Solución al Problema del "Topic se queda In Progress"

### Problema Original
```yaml
# ❌ ESTO NO FUNCIONA
Set variable:
  Var1 = $"<img src='data:image/png;base64,{Topic.Base64Aldo}'>"

Message:
  {Var1}  # ❌ No muestra la imagen, solo texto HTML
```

### Solución Correcta

#### Opción A: Usar API para convertir Base64 a URL

```yaml
# Nodo 1: HTTP Request (Convertir base64 a URL accesible)
Type: Call an action
Action: HTTP Request

Configuration:
  Method: POST
  URL: https://YOUR_API.azurecontainerapps.io/upload-temp-image
  
  Headers:
    - Content-Type: application/json
  
  Body:
    {
      "base64_data": "{Topic.Base64Aldo}",
      "employee_id": "temp_{randomGuid()}"
    }
  
  Save response as: Var_ImageResponse

# Nodo 2: Parse Response
Parse: Var_ImageResponse
Schema:
  image_url: string
Save as: Var_ImageURL

# Nodo 3: Show Adaptive Card
Type: Message

Card JSON:
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "Image",
      "url": "{Var_ImageURL}",
      "size": "Large"
    },
    {
      "type": "TextBlock",
      "text": "Foto de {Var_EmployeeName}",
      "weight": "Bolder"
    }
  ]
}
```

#### Opción B: Usar tabla pre-procesada (Recomendado)

```yaml
# ❌ NO uses base64 desde el Data Agent directamente

# ✅ SÍ usa photo_url (OneLake URL) desde employee_agent_view

# Nodo 1: Data Agent Query
Query: "Busca empleado Aldo en employee_agent_view"
Output:
  - photo_url → Var_PhotoURL  # Ya es una URL HTTP válida

# Nodo 2: Show Adaptive Card
Card JSON:
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "Image",
      "url": "{Var_PhotoURL}",  # ✅ URL directa desde Lakehouse
      "size": "Large"
    }
  ]
}
```

---

## 🎨 Ejemplo 4: Adaptive Card Template Completo

### Template Avanzado con Foto

```json
{
  "type": "AdaptiveCard",
  "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
  "version": "1.5",
  "body": [
    {
      "type": "Container",
      "style": "emphasis",
      "items": [
        {
          "type": "ColumnSet",
          "columns": [
            {
              "type": "Column",
              "width": "auto",
              "items": [
                {
                  "type": "Image",
                  "url": "{Var_PhotoURL}",
                  "size": "Large",
                  "style": "Person",
                  "altText": "{Var_EmpName}"
                }
              ]
            },
            {
              "type": "Column",
              "width": "stretch",
              "items": [
                {
                  "type": "TextBlock",
                  "text": "{Var_EmpName}",
                  "weight": "Bolder",
                  "size": "ExtraLarge"
                },
                {
                  "type": "TextBlock",
                  "text": "{Var_Position}",
                  "spacing": "None",
                  "size": "Medium",
                  "isSubtle": true
                },
                {
                  "type": "TextBlock",
                  "text": "📍 {Var_Department}",
                  "spacing": "Small",
                  "color": "Accent"
                },
                {
                  "type": "TextBlock",
                  "text": "🆔 {Var_EmpID}",
                  "spacing": "Small",
                  "size": "Small",
                  "isSubtle": true
                }
              ]
            }
          ]
        }
      ]
    },
    {
      "type": "Container",
      "separator": true,
      "spacing": "Medium",
      "items": [
        {
          "type": "TextBlock",
          "text": "Información de Contacto",
          "weight": "Bolder",
          "size": "Medium"
        },
        {
          "type": "FactSet",
          "facts": [
            {
              "title": "Email:",
              "value": "{Var_Email}"
            },
            {
              "title": "Teléfono:",
              "value": "{Var_Phone}"
            },
            {
              "title": "Ubicación:",
              "value": "{Var_Location}"
            }
          ]
        }
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "Ver perfil completo",
      "url": "https://yourcompany.com/profile/{Var_EmpID}"
    },
    {
      "type": "Action.Submit",
      "title": "Solicitar reunión",
      "data": {
        "action": "request_meeting",
        "employee_id": "{Var_EmpID}"
      }
    }
  ]
}
```

---

## 🚀 Configuración de Connections en Copilot Studio

### Connection 1: Fabric Data Agent

```yaml
Name: FabricDataAgent_EmployeeView
Type: Fabric Data Agent
Configuration:
  Workspace: YOUR_FABRIC_WORKSPACE
  SQL Endpoint: YOUR_LAKEHOUSE_SQL_ENDPOINT
  Default Table: employee_agent_view
  Authentication: Azure AD (Managed Identity)
```

### Connection 2: Image API

```yaml
Name: FabricImageAPI
Type: Custom Connector (HTTP)
Base URL: https://YOUR_API.azurecontainerapps.io

Actions:
  1. GetEmployeeImage:
     Path: /image/onelake/{employee_id}
     Method: GET
     Parameters:
       - employee_id (path, required)
       - thumbnail (query, optional, boolean)
  
  2. GenerateAdaptiveCard:
     Path: /adaptive-card/employee
     Method: GET
     Parameters:
       - employee_id (query, required)
       - employee_name (query, required)
       - department (query, required)
       - position (query, required)
       - api_base_url (query, required)

Authentication: None (public API) o API Key
```

### Connection 3: PowerPoint Generator

```yaml
Name: PPTGenerator
Type: Azure Function
Base URL: https://YOUR_FUNCTION_APP.azurewebsites.net/api

Actions:
  1. GeneratePPT:
     Path: /GeneratePPT
     Method: POST
     Body Schema:
       employees: array
       title: string
       subtitle: string
       use_ai_descriptions: boolean
     
     Response Schema:
       download_url: string
       file_name: string
       employee_count: number

Authentication: Function Key
```

---

## 📝 Variables Necesarias en Environment Variables

```bash
# Azure Container Apps (Image API)
FABRIC_WORKSPACE_ID=your-workspace-guid
FABRIC_LAKEHOUSE_ID=your-lakehouse-guid
AZURE_CLIENT_ID=your-managed-identity-client-id

# Azure Function (PPT Generator)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
FABRIC_API_ENDPOINT=https://YOUR_API.azurecontainerapps.io
STORAGE_ACCOUNT_NAME=yourpptsstorage
STORAGE_CONTAINER_NAME=presentations
```

---

## ✅ Testing Checklist

Antes de publicar tu agente, verifica:

- [ ] La tabla `employee_agent_view` existe en Fabric
- [ ] La API responde en: `https://YOUR_API.azurecontainerapps.io/`
- [ ] Puedes acceder a: `https://YOUR_API.azurecontainerapps.io/image/onelake/12345`
- [ ] El Data Agent retorna resultados con `photo_url`
- [ ] La Adaptive Card se renderiza correctamente en Test pane
- [ ] El PowerPoint se genera y descarga correctamente
- [ ] CORS está configurado para permitir Copilot Studio

---

## 🎯 Próximos Pasos

1. **Copiar configuración** de los ejemplos a tu Copilot Studio
2. **Reemplazar placeholders** (`YOUR_API`, `YOUR_FUNCTION_APP`, etc.)
3. **Probar Topic por Topic** en Test pane
4. **Publicar** cuando todo funcione
5. **Monitorear** en Analytics para ver uso real

¡Tu agente ahora puede mostrar imágenes profesionalmente! 🚀
