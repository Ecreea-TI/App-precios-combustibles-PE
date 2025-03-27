from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import pandas as pd
import requests
from io import BytesIO
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
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

def clear_cache():
    fetch_excel_data.cache_clear()
    get_cached_timestamp.cache_clear()

@lru_cache(maxsize=1)
def fetch_excel_data() -> List[Dict[Any, Any]]:
    # Check if cache is expired (1 hour)
    last_fetch = get_cached_timestamp()
    if datetime.now() - last_fetch > timedelta(hours=1):
        clear_cache()
    
    try:
        url = "https://www.osinergmin.gob.pe/seccion/centro_documental/hidrocarburos/SCOP/SCOP-DOCS/2025/Registro-precios/Ultimos-Precios-Registrados-EVPC.xlsx"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"Fetching data from {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        df = pd.read_excel(BytesIO(response.content))
        
        # Handle potential missing columns
        required_columns = ['FCHA_REGISTRO', 'DEPARTAMENTO', 'PROVINCIA', 'DISTRITO']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {', '.join(missing_columns)}")
            clear_cache()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Formato de archivo Excel no válido: columnas faltantes: {', '.join(missing_columns)}"
            )
            
        # Convert date column to standard format
        df['FCHA_REGISTRO'] = pd.to_datetime(df['FCHA_REGISTRO'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Replace NaN values with None for proper JSON serialization
        df = df.where(pd.notnull(df), None)
        
        logger.info(f"Successfully fetched {len(df)} records")
        return df.to_dict('records')
        
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching Excel file")
        clear_cache()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Tiempo de espera agotado al intentar acceder al archivo Excel"
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while fetching Excel file: {str(e)}")
        clear_cache()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se pudo acceder al archivo Excel. Por favor, inténtelo de nuevo más tarde."
        )
    except pd.errors.ParserError as e:
        logger.error(f"Error parsing Excel file: {str(e)}")
        clear_cache()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar el archivo Excel. El formato del archivo puede haber cambiado."
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching Excel data: {str(e)}")
        clear_cache()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al obtener los datos. Por favor, inténtelo de nuevo más tarde."
        )

@app.get("/api/precios", response_model=List[Dict[Any, Any]])
async def get_prices(
    departamento: Optional[str] = Query(None, description="Filter by department"),
    provincia: Optional[str] = Query(None, description="Filter by province"),
    distrito: Optional[str] = Query(None, description="Filter by district")
):
    try:
        data = fetch_excel_data()
        
        if departamento:
            data = [item for item in data if item.get('DEPARTAMENTO') == departamento]
        if provincia:
            data = [item for item in data if item.get('PROVINCIA') == provincia]
        if distrito:
            data = [item for item in data if item.get('DISTRITO') == distrito]
            
        return data
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing request"
        )

handler = Mangum(app)