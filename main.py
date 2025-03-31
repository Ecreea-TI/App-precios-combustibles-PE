from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import os
from functools import lru_cache

# Configure logging
logger = logging.getLogger("api-precios")

app = FastAPI(
    title="Precios de Combustibles API",
    description="API para consultar precios de combustibles de Osinergmin",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache the data for 1 hour to avoid excessive requests to the source
@lru_cache(maxsize=1)
def get_cached_timestamp():
    return datetime.now()

@lru_cache(maxsize=1)
def fetch_excel_data(max_retries: int = 3) -> List[Dict[Any, Any]]:
    """Fetch and process the Excel data from Osinergmin with retry mechanism.
    
    Args:
        max_retries (int): Maximum number of retry attempts
    
    Returns:
        List[Dict[Any, Any]]: List of dictionaries containing fuel price data
    
    Raises:
        HTTPException: If the Excel file cannot be accessed or processed after retries
    """
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Check if cache is expired (1 hour)
            last_fetch = get_cached_timestamp()
            if datetime.now() - last_fetch > timedelta(hours=1):
                fetch_excel_data.cache_clear()
                get_cached_timestamp.cache_clear()
            
            url = "https://www.osinergmin.gob.pe/seccion/centro_documental/hidrocarburos/SCOP/SCOP-DOCS/2025/Registro-precios/Ultimos-Precios-Registrados-EVPC.xlsx"
            
            logger.info(f"Intento {retry_count + 1} de {max_retries} para obtener datos de {url}")
            response = requests.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/json',
                    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
                },
                timeout=30
            )
            response.raise_for_status()
            
            df = pd.read_excel(BytesIO(response.content))
            
            # Verificar columnas requeridas
            required_columns = ['FCHA_REGISTRO', 'DEPARTAMENTO', 'PROVINCIA', 'DISTRITO', 'RAZON']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Columnas faltantes en el archivo Excel: {', '.join(missing_columns)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"El formato del archivo Excel ha cambiado. Columnas faltantes: {', '.join(missing_columns)}"
                )
            
            # Convertir fecha a formato estándar
            df['FCHA_REGISTRO'] = pd.to_datetime(df['FCHA_REGISTRO'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Reemplazar valores NaN con None
            df = df.where(pd.notnull(df), None)
            
            logger.info(f"Datos obtenidos exitosamente: {len(df)} registros")
            return df.to_dict(orient='records')
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            retry_count += 1
            last_error = e
            logger.warning(f"Intento {retry_count} de {max_retries} falló: {str(e)}")
            
            if retry_count < max_retries:
                time.sleep(2 ** retry_count)  # Espera exponencial
                continue
                
            logger.error("Error de conexión persistente al intentar acceder al archivo Excel")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"No se pudo acceder al archivo Excel después de {max_retries} intentos. Por favor, inténtelo más tarde."
            )
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error HTTP al obtener el archivo Excel: {str(e)}")
            if e.response.status_code == 403:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acceso denegado al archivo Excel. Por favor, inténtelo más tarde."
                )
            elif e.response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="El archivo Excel no se encuentra disponible en este momento."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al acceder al archivo Excel (código {e.response.status_code})"
                )
                
        except pd.errors.ParserError as e:
            logger.error(f"Error al procesar el archivo Excel: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al procesar el archivo Excel. El formato del archivo puede haber cambiado."
            )
            
        except Exception as e:
            logger.error(f"Error inesperado al obtener datos: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error inesperado al procesar los datos: {str(e)}"
            )
    
    # Si llegamos aquí, todos los intentos fallaron
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="El servicio no está disponible en este momento. Por favor, inténtelo más tarde."
    )

# Mount static files directory
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", status_code=status.HTTP_200_OK)
async def root():
    """Root endpoint that returns the web interface."""
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/precios", status_code=status.HTTP_200_OK)
async def get_precios():
    """Get all fuel prices from the dataset."""
    try:
        data = fetch_excel_data()
        return {
            "status": "success",
            "total_registros": len(data),
            "fecha_consulta": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_precios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error al procesar la solicitud: {str(e)}"
        )

@app.get("/departamentos", status_code=status.HTTP_200_OK)
async def get_departamentos():
    """Get a list of all available departments."""
    try:
        data = fetch_excel_data()
        available_departments = sorted(list({item['DEPARTAMENTO'] for item in data if item.get('DEPARTAMENTO')}))
        
        return {
            "status": "success",
            "total_departamentos": len(available_departments),
            "fecha_consulta": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "departamentos": available_departments
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_departamentos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error al procesar la solicitud: {str(e)}"
        )

@app.get("/precios/{departamento}", status_code=status.HTTP_200_OK)
async def get_precios_por_departamento(departamento: str):
    """Get fuel prices filtered by department."""
    try:
        if not departamento or len(departamento.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="El departamento no puede estar vacío"
            )

        data = fetch_excel_data()
        
        # Normalize department name
        departamento = departamento.strip().upper()
        
        # Check if department exists in data
        available_departments = {item.get('DEPARTAMENTO') for item in data if item.get('DEPARTAMENTO')}
        if departamento not in available_departments:
            return {
                "status": "success",
                "departamento": departamento,
                "total_registros": 0,
                "fecha_consulta": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data": [],
                "available_departments": sorted(list(available_departments))
            }

        filtered_data = [
            item for item in data 
            if item.get('DEPARTAMENTO') == departamento
        ]
        
        return {
            "status": "success",
            "departamento": departamento,
            "total_registros": len(filtered_data),
            "fecha_consulta": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "data": filtered_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_precios_por_departamento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error al procesar la solicitud: {str(e)}"
        )