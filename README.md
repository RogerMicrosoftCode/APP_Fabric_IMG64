# 📸 OHR Agent - Imágenes en Copilot Studio con Adaptive Cards

**Solución para mostrar fotos de empleados en Copilot Studio usando Fabric Data Agent**

---

## 🎯 Problema Resuelto

Tu agente "OHR Agent" en Copilot Studio consulta datos de empleados desde Fabric (originados en Snowflake), pero las imágenes **NO se muestran** correctamente:

- ❌ **Antes**: Data Agent devuelve HTML escapado → Copilot muestra texto plano
- ✅ **Después**: Adaptive Cards con URLs HTTP → Copilot muestra imágenes renderizadas

---

## 🏗️ Arquitectura

```
Snowflake (TDS, LMD, SHD)
    ↓
PRD_TDS_GBL_OHR (Mirrored Database en Fabric)
    ↓
OHR Base64 Image Parser (Tu Notebook actual)
    ↓ +Modificación: Agregar celda para guardar archivos JPG
OHR Lakehouse Files (/employee_photos/*.jpg)
    ↓
OHR_Employee_Agent_View (Tabla con URLs OneLake)
    ↓
OHR Agent (Fabric Data Agent)
    ↓
Copilot Studio Topic con Adaptive Cards
    ↓
✅ Imagen visible + PowerPoint con Azure OpenAI
```

---

## 📚 Documentación

### 🚀 Para Implementar

**[SOLUCION_DATA_AGENT_OHR.md](./SOLUCION_DATA_AGENT_OHR.md)** - Guía completa paso a paso

### 🎨 Recursos

| Archivo | Uso |
|---------|-----|
| **[adaptive_card_employee_template.json](./adaptive_card_employee_template.json)** | Template para Copilot Studio Topic (copiar/pegar) |
| **[generate_ppt_with_openai.py](./generate_ppt_with_openai.py)** | Azure Function para generar PowerPoint automático |

---

## ⚡ Quick Start (3 Pasos)

### 1️⃣ Modificar tu Notebook Actual

En **OHR Base64 Image Parser**, agrega esta celda al final:

```python
# Guardar imágenes como archivos JPG en Lakehouse
from notebookutils import mssparkutils
import base64

def save_base64_to_lakehouse(base64_string, employee_id):
    if ',' in base64_string:
        base64_data = base64_string.split(',')[1]
    else:
        base64_data = base64_string
    
    image_bytes = base64.b64decode(base64_data)
    file_path = f"/lakehouse/default/Files/employee_photos/{employee_id}.jpg"
    mssparkutils.fs.put(file_path, image_bytes, overwrite=True)
    
    workspace_id = spark.conf.get("trident.workspace.id")
    lakehouse_id = spark.conf.get("trident.lakehouse.id")
    
    return f"https://onelake.dfs.fabric.microsoft.com/{workspace_id}/{lakehouse_id}/Files/employee_photos/{employee_id}.jpg"

# Aplicar a tu DataFrame
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

save_photo_udf = udf(save_base64_to_lakehouse, StringType())

df_with_urls = df_employees.withColumn("photo_url", save_photo_udf("photo_base64", "employee_id"))

# Guardar tabla para Data Agent
df_with_urls.write.format("delta").mode("overwrite").saveAsTable("OHR_Employee_Agent_View")
```

### 2️⃣ Actualizar Data Agent

1. En Fabric, ve a **OHR Agent** → Settings
2. Data sources → **Add** → `OHR_Employee_Agent_View`
3. Save

### 3️⃣ Configurar Topic con Adaptive Card

En Copilot Studio, tu Topic debe tener esta estructura:

```
Trigger: "dame la foto de {EmployeeName}"
  ↓
Create generative answers (OHR Agent)
  → Output: Topic.DataResponse
  ↓
Parse JSON:
  Topic.PhotoURL = Topic.DataResponse.SearchQueryResult.value[0].photo_url
  Topic.EmployeeName = Topic.DataResponse.SearchQueryResult.value[0].employee_name
  ↓
Send Adaptive Card (ver template en adaptive_card_employee_template.json)
```

**Copia el JSON de** [adaptive_card_employee_template.json](./adaptive_card_employee_template.json) en tu nodo "Send a message" tipo "Adaptive Card".

---

## 🎨 Adaptive Card Template

```json
{
  "type": "AdaptiveCard",
  "version": "1.5",
  "body": [
    {
      "type": "Image",
      "url": "${Topic.PhotoURL}",
      "size": "Large",
      "style": "Person"
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

## 📊 Generar PowerPoint (Opcional)

Despliega **[generate_ppt_with_openai.py](./generate_ppt_with_openai.py)** como Azure Function:

```bash
func init EmployeePPTGenerator --python
cd EmployeePPTGenerator
# Copiar generate_ppt_with_openai.py
func azure functionapp publish employee-ppt-api
```

Agrega botón en Adaptive Card:

```json
{
  "type": "ActionSet",
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

---

## 🧪 Testing

| Prueba | Comando | Resultado Esperado |
|--------|---------|-------------------|
| **1. Verificar archivos** | En Fabric: `Files/employee_photos/` | Archivos .jpg creados |
| **2. Verificar tabla** | `SELECT photo_url FROM OHR_Employee_Agent_View LIMIT 5` | URLs OneLake válidas |
| **3. Probar Topic** | "dame la foto de Aldo" | ✅ Imagen renderizada en chat |
| **4. PowerPoint** | Click botón "Generar PowerPoint" | ✅ Descarga .pptx con foto |

---

## 🐛 Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| Imagen muestra icono roto 🖼️❌ | URL OneLake no accesible | Verificar permisos: Data Agent necesita acceso a Lakehouse Files |
| Data Agent no devuelve resultados | Tabla no indexada | Esperar 5 min después de crear OHR_Employee_Agent_View |
| `Topic.PhotoURL` está vacío | Parsing incorrecto | Verificar path: `Topic.DataResponse.SearchQueryResult.value[0].photo_url` |

---

## 📞 Soporte

Para más detalles, ver **[SOLUCION_DATA_AGENT_OHR.md](./SOLUCION_DATA_AGENT_OHR.md)**.

---

## ✅ Checklist de Implementación

- [ ] Modificar notebook: Agregar celda de `save_base64_to_lakehouse()`
- [ ] Ejecutar notebook: Crear archivos JPG en Lakehouse Files
- [ ] Verificar: Confirmar archivos en `/Files/employee_photos/`
- [ ] Crear tabla: `OHR_Employee_Agent_View` con columna `photo_url`
- [ ] Actualizar Data Agent: Agregar nueva tabla como data source
- [ ] Configurar Topic: Parse JSON del Data Agent response
- [ ] Copiar Adaptive Card: Pegar JSON template en Topic
- [ ] Probar: "dame la foto de Aldo" → Imagen visible ✅
- [ ] (Opcional) Desplegar Azure Function para PowerPoint
- [ ] (Opcional) Agregar botón "Generar PowerPoint" en Adaptive Card

---

**🎯 Resultado Final**: Copilot Studio muestra fotos de empleados profesionalmente con Adaptive Cards + opción de generar PowerPoint automático. 🚀
