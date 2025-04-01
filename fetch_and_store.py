import requests
import pandas as pd
from io import BytesIO
from datetime import datetime
import logging
import os
from sqlalchemy import create_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fetch_and_store")

# Database configuration
DATABASE_URL = 'postgresql://admin:3qLTiZnH1cgX7a5InAryAgqqMVFXXy9d@dpg-cvlvv3u3jp1c738rf1og-a/data_excel'



def fetch_excel_data() -> pd.DataFrame:
    """Fetch and process the Excel data from Osinergmin.

    Returns:
        pd.DataFrame: DataFrame containing fuel price data

    Raises:
        Exception: If any error occurs during fetching or processing
    """
    url = "https://www.osinergmin.gob.pe/seccion/centro_documental/hidrocarburos/SCOP/SCOP-DOCS/2025/Registro-precios/Ultimos-Precios-Registrados-EVPC.xlsx"

    try:
        logger.info(f"Fetching data from {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        df = pd.read_excel(BytesIO(response.content))

        # Handle potential missing columns
        if 'FCHA_REGISTRO' not in df.columns:
            logger.error("Column 'FCHA_REGISTRO' not found in Excel file")
            raise ValueError("Formato de archivo Excel no válido: columna 'FCHA_REGISTRO' no encontrada")

        # Convert date column to standard format
        df['FCHA_REGISTRO'] = pd.to_datetime(df['FCHA_REGISTRO'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

        # Replace NaN values with None for proper database storage
        df = df.where(pd.notnull(df), None)

        logger.info(f"Successfully fetched {len(df)} records")
        return df

    except Exception as e:
        logger.error(f"Error fetching Excel data: {str(e)}")
        raise

def store_data(df: pd.DataFrame):
    """Store the processed data in the database.

    Args:
        df (pd.DataFrame): Processed DataFrame to store

    Raises:
        Exception: If any error occurs during database operations
    """
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            df.to_sql('fuel_prices', connection, if_exists='append', index=False)
        logger.info(f"Successfully stored {len(df)} records in database")
    except Exception as e:
        logger.error(f"Error storing data: {str(e)}")
        raise

def main():
    """Main function to fetch and store data"""
    try:
        df = fetch_excel_data()
        store_data(df)
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise

if __name__ == "__main__":
    main()