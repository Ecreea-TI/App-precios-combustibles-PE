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

@lru_cache(maxsize=1)
def fetch_excel_data() -> List[Dict[Any, Any]]:
    try:
        url = "https://www.osinergmin.gob.pe/seccion/centro_documental/hidrocarburos/SCOP/SCOP-DOCS/2023/Regresiondatos.xlsx"
        response = requests.get(url)
        response.raise_for_status()
        
        df = pd.read_excel(BytesIO(response.content))
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Error accessing Osinergmin data"
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