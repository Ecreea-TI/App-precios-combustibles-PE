import requests
import json

print('Checking API response...')
try:
    response = requests.get('http://localhost:8000/precios')
    data = response.json()
    
    print('\nAPI Response Status:', data.get('status'))
    print('Total Records:', data.get('total_registros'))
    
    if data.get('data') and len(data['data']) > 0:
        first_record = data['data'][0]
        
        print('\nFirst record keys:')
        for key in first_record.keys():
            print(f'- {key}')
        
        print('\nFirst record values:')
        for key, value in first_record.items():
            print(f'{key}: {value}')
            
        # Specifically check for Razón Social and Precio fields
        print('\nChecking specific fields:')
        print(f"RAZON_SOCIAL exists: {'RAZON_SOCIAL' in first_record}")
        if 'RAZON_SOCIAL' in first_record:
            print(f"RAZON_SOCIAL value: {first_record['RAZON_SOCIAL']}")
        
        print(f"PRECIO exists: {'PRECIO' in first_record}")
        if 'PRECIO' in first_record:
            print(f"PRECIO value: {first_record['PRECIO']}")
    else:
        print('No data records found in the response')
        
except Exception as e:
    print(f'Error: {str(e)}')