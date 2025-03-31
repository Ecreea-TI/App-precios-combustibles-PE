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
def fetch_excel_data() -> List[Dict[Any, Any]]:
    """Fetch and process the Excel data from Osinergmin.
    
    Returns:
        List[Dict[Any, Any]]: List of dictionaries containing fuel price data
    
    Raises:
        HTTPException: If the Excel file cannot be accessed or processed
    """
    # Check if cache is expired (1 hour)
    last_fetch = get_cached_timestamp()
    if datetime.now() - last_fetch > timedelta(hours=1):
        # Clear cache to force refresh
        fetch_excel_data.cache_clear()
        get_cached_timestamp.cache_clear()
    
    url = "https://www.osinergmin.gob.pe/seccion/centro_documental/hidrocarburos/SCOP/SCOP-DOCS/2025/Registro-precios/Ultimos-Precios-Registrados-EVPC.xlsx"
    
    try:
        logger.info(f"Fetching data from {url}")
        response = requests.get(url, timeout=10)  # Add timeout
        response.raise_for_status()  # Raise exception for HTTP errors
        
        df = pd.read_excel(BytesIO(response.content))
        
        # Handle potential missing columns
        if 'FCHA_REGISTRO' not in df.columns:
            logger.error("Column 'FCHA_REGISTRO' not found in Excel file")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Formato de archivo Excel no válido: columna 'FCHA_REGISTRO' no encontrada"
            )
            
        # Convert date column to standard format
        df['FCHA_REGISTRO'] = pd.to_datetime(df['FCHA_REGISTRO'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Replace NaN values with None for proper JSON serialization
        df = df.where(pd.notnull(df), None)
        
        logger.info(f"Successfully fetched {len(df)} records")
        return df.to_dict(orient='records')
        
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching Excel file")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, 
            detail="Tiempo de espera agotado al intentar acceder al archivo Excel"
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while fetching Excel file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No se pudo acceder al archivo Excel"
        )
    except pd.errors.ParserError as e:
        logger.error(f"Error parsing Excel file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error al procesar el archivo Excel"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching Excel data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error inesperado: {str(e)}"
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