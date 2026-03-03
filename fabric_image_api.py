"""
Fabric Image API - FastAPI para servir imágenes almacenadas en Lakehouse
Permite convertir base64 y OneLake URLs en endpoints HTTP accesibles para agentes

Deploy en Azure Container Apps o Azure Functions
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
import io
from PIL import Image
import requests
from typing import Optional
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

app = FastAPI(
    title="Fabric Image Service",
    description="API para servir imágenes desde Fabric Lakehouse",
    version="1.0.0"
)

# CORS para permitir acceso desde Copilot Studio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de Fabric Lakehouse (OneLake)
WORKSPACE_ID = os.getenv("FABRIC_WORKSPACE_ID", "your-workspace-id")
LAKEHOUSE_ID = os.getenv("FABRIC_LAKEHOUSE_ID", "your-lakehouse-id")


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "service": "Fabric Image API",
        "status": "healthy",
        "endpoints": {
            "base64": "/image/base64?data=<base64_string>",
            "onelake": "/image/onelake?employee_id=<id>",
            "adaptive_card": "/adaptive-card/employee?id=<employee_id>"
        }
    }


@app.get("/image/base64")
def serve_base64_image(
    data: str = Query(..., description="Base64 encoded image data"),
    format: str = Query("jpeg", description="Image format (jpeg, png, webp)"),
    max_width: Optional[int] = Query(None, description="Max width for resize"),
    max_height: Optional[int] = Query(None, description="Max height for resize")
):
    """
    Sirve imagen desde base64
    
    Ejemplo:
    /image/base64?data=iVBORw0KGgo...&format=jpeg&max_width=300
    """
    try:
        # Limpiar base64 (remover data URI si existe)
        if ',' in data:
            data = data.split(',')[1]
        
        # Decodificar
        image_data = base64.b64decode(data)
        image = Image.open(io.BytesIO(image_data))
        
        # Redimensionar si se especifica
        if max_width and max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Convertir a bytes
        buffer = io.BytesIO()
        image_format = format.upper()
        if image_format == 'JPG':
            image_format = 'JPEG'
        
        image.save(buffer, format=image_format, quality=85)
        buffer.seek(0)
        
        # Determinar MIME type
        mime_types = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png',
            'WEBP': 'image/webp'
        }
        
        return StreamingResponse(
            buffer,
            media_type=mime_types.get(image_format, 'image/jpeg')
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando imagen: {str(e)}")


@app.get("/image/onelake/{employee_id}")
def serve_onelake_image(
    employee_id: str,
    thumbnail: bool = Query(False, description="Return thumbnail (150x150)")
):
    """
    Sirve imagen desde OneLake usando Fabric API
    
    Ejemplo:
    /image/onelake/12345?thumbnail=true
    """
    try:
        # Construir URL de OneLake
        onelake_url = f"https://onelake.dfs.fabric.microsoft.com/{WORKSPACE_ID}/{LAKEHOUSE_ID}/Files/employee_photos/{employee_id}.jpg"
        
        # Obtener credenciales de Azure
        credential = DefaultAzureCredential()
        token = credential.get_token("https://storage.azure.com/.default")
        
        # Descargar imagen
        headers = {
            'Authorization': f'Bearer {token.token}',
            'x-ms-version': '2021-08-06'
        }
        
        response = requests.get(onelake_url, headers=headers)
        response.raise_for_status()
        
        if thumbnail:
            # Crear thumbnail
            image = Image.open(io.BytesIO(response.content))
            image.thumbnail((150, 150), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=75)
            buffer.seek(0)
            
            return StreamingResponse(buffer, media_type='image/jpeg')
        
        return Response(content=response.content, media_type='image/jpeg')
        
    except requests.HTTPError as e:
        raise HTTPException(status_code=404, detail=f"Imagen no encontrada: {employee_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo imagen: {str(e)}")


@app.get("/adaptive-card/employee")
def generate_adaptive_card(
    employee_id: str = Query(..., description="Employee ID"),
    employee_name: str = Query(..., description="Employee name"),
    department: str = Query(..., description="Department"),
    position: str = Query(..., description="Position"),
    api_base_url: str = Query(..., description="Base URL of this API")
):
    """
    Genera Adaptive Card con foto de empleado
    Usar en Copilot Studio para mostrar imágenes
    
    Ejemplo:
    /adaptive-card/employee?employee_id=12345&employee_name=Pamela%20Yissell&department=HR&position=Manager&api_base_url=https://your-api.azurecontainerapps.io
    """
    
    image_url = f"{api_base_url}/image/onelake/{employee_id}?thumbnail=true"
    
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [
                            {
                                "type": "Image",
                                "url": image_url,
                                "size": "Medium",
                                "style": "Person",
                                "altText": employee_name
                            }
                        ]
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [
                            {
                                "type": "TextBlock",
                                "text": employee_name,
                                "weight": "Bolder",
                                "size": "Large"
                            },
                            {
                                "type": "TextBlock",
                                "text": position,
                                "spacing": "None",
                                "isSubtle": True
                            },
                            {
                                "type": "TextBlock",
                                "text": f"📍 {department}",
                                "spacing": "Small",
                                "wrap": True
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    return card


@app.get("/batch/adaptive-cards")
def generate_batch_cards(
    employee_ids: str = Query(..., description="Comma-separated employee IDs"),
    api_base_url: str = Query(..., description="Base URL of this API")
):
    """
    Genera múltiples Adaptive Cards para varios empleados
    
    Ejemplo:
    /batch/adaptive-cards?employee_ids=12345,67890&api_base_url=https://your-api.com
    
    Retorna: Lista de Adaptive Cards para usar en PowerPoint o Copilot
    """
    
    ids = employee_ids.split(',')
    
    # En producción, consultar Fabric Data Warehouse para obtener datos
    # Por ahora retornamos template
    
    cards = []
    for emp_id in ids:
        image_url = f"{api_base_url}/image/onelake/{emp_id.strip()}"
        
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.5",
            "body": [
                {
                    "type": "Image",
                    "url": image_url,
                    "size": "Large"
                },
                {
                    "type": "TextBlock",
                    "text": f"Employee ID: {emp_id}",
                    "weight": "Bolder"
                }
            ]
        }
        cards.append(card)
    
    return {"cards": cards, "count": len(cards)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


"""
DEPLOYMENT INSTRUCTIONS
=======================

1. Azure Container Apps (Recomendado):
   
   az containerapp create \
     --name fabric-image-api \
     --resource-group YOUR_RG \
     --environment YOUR_ENV \
     --image YOUR_ACR.azurecr.io/fabric-image-api:latest \
     --target-port 8000 \
     --ingress external \
     --min-replicas 1 \
     --max-replicas 3 \
     --env-vars \
       FABRIC_WORKSPACE_ID=your-workspace-id \
       FABRIC_LAKEHOUSE_ID=your-lakehouse-id

2. Azure Functions (Alternativa):
   - Usar Azure Functions Python con HttpTrigger
   - Configurar CORS para Copilot Studio

3. Configurar en Copilot Studio:
   
   a. Crear Action:
      - Type: HTTP Request
      - URL: https://your-api.azurecontainerapps.io/adaptive-card/employee
      - Method: GET
      - Parameters: employee_id, employee_name, department, position, api_base_url
   
   b. En Topic, usar la respuesta:
      - Parse JSON response
      - Send Adaptive Card usando el JSON retornado

4. Testing local:
   
   uvicorn fabric_image_api:app --reload
   
   Probar en: http://localhost:8000/docs
"""
