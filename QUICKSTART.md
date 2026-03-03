# ⚡ Guía de Inicio Rápido - Fabric Data Agent con Imágenes

> Implementa procesamiento de imágenes base64 en tu agente OHR en menos de 15 minutos

---

## 🎯 Objetivo

Configurar tu Fabric Data Agent para mostrar fotografías de empleados almacenadas en formato base64.

---

## 📋 Pre-requisitos

- ✅ Microsoft Fabric workspace configurado
- ✅ Tabla con campo `PhotoBase64` (tipo STRING)
- ✅ Fabric Data Agent creado (agente OHR)
- ✅ Permisos para crear tablas Delta

---

## 🚀 Pasos de Implementación

### Paso 1: Preparar el Notebook (3 min)

```python
# 1. Crear nuevo notebook en Fabric
# 2. Copiar el contenido de 'fabric_notebook_image_processing.py'
# 3. Pegar en el notebook de Fabric
```

### Paso 2: Configurar Variables (2 min)

Ajusta estas líneas en el notebook:

```python
# En la Celda 4 - Ajustar nombre de tabla
tabla_empleados = 'hr_database.employees'  # 🔧 CAMBIAR AQUÍ

# En la Celda 5 - Ajustar nombres de campos (si son diferentes)
campo_foto = 'PhotoBase64'    # Campo con base64
campo_id = 'EmployeeID'       # Campo con ID del empleado
```

### Paso 3: Ejecutar el Notebook (5 min)

```bash
# Ejecuta todas las celdas en orden:
# Celda 1: Instalación de Pillow
# Celda 2: Imports
# Celda 3: Definir funciones
# Celda 4: Leer datos
# Celda 5: Procesar imágenes
# Celda 6: Crear content_table
# Celda 7: Guardar tabla física
# Celda 8: Verificación
```

**Resultado esperado:**
```
✅ Funciones registradas correctamente
✅ Imágenes procesadas
✅ Content table generado
✅ Tabla guardada: hr_database.ohr_agent_content_table
📊 Total registros: [número]
```

### Paso 4: Configurar el Agente (3 min)

1. Ve a Fabric Data Agent
2. Abre tu agente **OHR Agent**
3. Click en ⚙️ **Edit configuration**
4. Navega a **Content Protocol**
5. En **Content Table**, selecciona:
   ```
   hr_database.ohr_agent_content_table
   ```
6. Mapea las columnas:
   | Columna Tabla | Campo Agente |
   |---------------|--------------|
   | annotations   | annotations  |
   | meta          | meta         |
   | text          | text         |
7. Click **Save**

### Paso 5: Probar el Agente (2 min)

Prueba con estos comandos:

```
💬 "Dame información del empleado 102025"
💬 "Muéstrame los datos de Gerardo"
💬 "Quién es el empleado con ID 102025"
```

**✅ Deberías ver la información CON la foto del empleado!**

---

## 🎨 Ejemplo de Output Esperado

```markdown
**Información del Empleado ID: 102025**

---

### Fotografía
[Imagen del empleado renderizada aquí - 300x300px]

---

### Datos Personales
- **Nombre Completo:** Gerardo Silvestre Reyna Camacho
- **Posición:** Manager Data Architecture & Engineering
- **Departamento:** IT
```

---

## 🔧 Verificación Rápida

### ¿Todo funcionó?

Ejecuta este query para verificar:

```python
# En tu notebook de Fabric
spark.sql("""
    SELECT 
        EmployeeID,
        CASE 
            WHEN employee_photo_html LIKE '%<img%' THEN '✅ Con foto'
            WHEN employee_photo_html LIKE '%👤%' THEN '⚠️ Placeholder'
            ELSE '❌ Error'
        END as status
    FROM hr_database.ohr_agent_content_table
    LIMIT 10
""").show()
```

---

## ❌ Troubleshooting Express

### Problema 1: "No veo imágenes"

**Solución rápida:**
```python
# Verifica que PhotoBase64 tenga datos
df = spark.table('hr_database.employees')
df.filter(F.col('PhotoBase64').isNotNull()).count()
# Si es 0, no hay imágenes en la tabla origen
```

### Problema 2: "Error en el notebook"

**Solución rápida:**
```python
# Reinstala Pillow
%pip install --force-reinstall Pillow==10.2.0

# Reinicia el kernel
# Kernel → Restart Kernel
```

### Problema 3: "Agente no encuentra datos"

**Solución rápida:**
```sql
-- Verifica que la tabla existe
SHOW TABLES IN hr_database LIKE 'ohr_agent_content_table';

-- Verifica que tiene datos
SELECT COUNT(*) FROM hr_database.ohr_agent_content_table;
```

---

## 📊 Validación Final

### Checklist de Éxito

- [ ] Notebook ejecutado sin errores
- [ ] Tabla `ohr_agent_content_table` creada con datos
- [ ] Content Protocol configurado en el agente
- [ ] Query de prueba retorna información con foto
- [ ] Placeholder se muestra si no hay foto

---

## 🎉 ¡Felicidades!

Si completaste todos los pasos, tu agente OHR ahora puede:

- ✅ Mostrar fotografías de empleados automáticamente
- ✅ Manejar casos sin foto con placeholders elegantes
- ✅ Procesar imágenes optimizadas (300x300px)
- ✅ Funcionar con tablas físicas (compatible con Fabric)

---

## 📚 Siguientes Pasos

### Mejoras Recomendadas

1. **Automatización**: Configura Fabric Pipelines para ejecutar el notebook diariamente
2. **Monitoreo**: Agrega alertas si >5% de imágenes fallan
3. **Optimización**: Ajusta `max_width` según tu necesidad
4. **Backup**: Configura backups automáticos de la tabla

---

## 🆘 ¿Necesitas Ayuda?

Si algo no funciona:

1. Revisa la sección **Troubleshooting** en el README.md principal
2. Verifica los logs del notebook (Output de cada celda)
3. Consulta la documentación completa en `Guia_Fabric_Imagenes_Base64.docx`

---

<div align="center">

**Tiempo total estimado: 15 minutos**

🚀 **¡A implementar!** 🚀

</div>
