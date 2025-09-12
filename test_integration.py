"""
Script para testear la integración PostgreSQL + DuckDB
Ejecutar: python test_integration.py
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_integrated_endpoints():
    """Testa los nuevos endpoints integrados"""
    
    async with httpx.AsyncClient() as client:
        print("=== Test de Integración PostgreSQL + DuckDB ===\n")
        
        # 1. Test: Lista archivos combinados
        print("1. Testing GET /files (combined data)...")
        try:
            response = await client.get(f"{BASE_URL}/files")
            if response.status_code == 200:
                files = response.json()
                print(f"✅ Found {len(files)} files with combined data")
                
                if files:
                    # Mostrar primer archivo como ejemplo
                    first_file = files[0]
                    print(f"   Example file: {first_file['name']}")
                    print(f"   Title: {first_file.get('title', 'No metadata')}")
                    print(f"   Responsible: {first_file.get('responsible', 'N/A')}")
                    print(f"   Row count: {first_file.get('row_count', 'N/A')}")
                    print(f"   Tags: {first_file.get('tags', [])}")
            else:
                print(f"❌ Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        
        # 2. Test: Búsqueda con filtros
        print("2. Testing GET /files with search filters...")
        try:
            response = await client.get(f"{BASE_URL}/files?search=retail")
            if response.status_code == 200:
                files = response.json()
                print(f"✅ Search 'retail' found {len(files)} files")
            else:
                print(f"❌ Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        
        # 3. Test: Info combinada de archivo específico
        print("3. Testing GET /files/{filename}/info (combined)...")
        try:
            # Usar un archivo que sabemos que existe
            test_filename = "ventas_retail_2024.parquet"  # Del init.sql
            response = await client.get(f"{BASE_URL}/files/{test_filename}/info")
            if response.status_code == 200:
                file_info = response.json()
                print(f"✅ Combined info for {test_filename}:")
                print(f"   Technical data: {file_info.get('size_mb', 'N/A')} MB")
                print(f"   Metadata: {file_info.get('title', 'No title')}")
                print(f"   Description: {file_info.get('description', 'No description')[:50]}...")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        
        # 4. Test: Obtener filtros únicos
        print("4. Testing filter endpoints...")
        try:
            response = await client.get(f"{BASE_URL}/metadata/filters/responsibles")
            if response.status_code == 200:
                responsibles = response.json()["responsibles"]
                print(f"✅ Found {len(responsibles)} unique responsibles: {responsibles}")
            
            response = await client.get(f"{BASE_URL}/metadata/filters/tags")
            if response.status_code == 200:
                tags = response.json()["tags"]
                print(f"✅ Found {len(tags)} unique tags: {tags[:5]}...")  # Mostrar primeros 5
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        
        # 5. Test: Crear metadatos nuevos
        print("5. Testing POST /metadata (create)...")
        try:
            new_metadata = {
                "filename": "test_file.parquet",
                "title": "Archivo de Test",
                "description": "Archivo creado para testing de la API",
                "responsible": "Test User",
                "frequency": "Manual",
                "permissions": "private",
                "tags": ["test", "api", "demo"]
            }
            
            response = await client.post(f"{BASE_URL}/metadata", json=new_metadata)
            if response.status_code == 200:
                created = response.json()
                print(f"✅ Created metadata for test_file.parquet (ID: {created['id']})")
            elif response.status_code == 400:
                print("⚠️  Metadata already exists (expected on second run)")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        
        # 6. Test: Actualizar metadatos
        print("6. Testing PUT /metadata/{filename} (update)...")
        try:
            update_data = {
                "description": "Descripción actualizada desde el test",
                "tags": ["test", "api", "demo", "updated"]
            }
            
            response = await client.put(
                f"{BASE_URL}/metadata/test_file.parquet?changed_by=test_user",
                json=update_data
            )
            if response.status_code == 200:
                updated = response.json()
                print(f"✅ Updated metadata: {updated['description'][:50]}...")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        
        # 7. Test: Historial de cambios
        print("7. Testing GET /metadata/{filename}/history...")
        try:
            response = await client.get(f"{BASE_URL}/metadata/test_file.parquet/history")
            if response.status_code == 200:
                history = response.json()
                print(f"✅ Found {len(history)} history entries")
                if history:
                    latest = history[0]
                    print(f"   Latest change: {latest['field_changed']} by {latest['changed_by']}")
            else:
                print(f"❌ Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        
        # 8. Test: Sincronización
        print("8. Testing POST /sync/all-files...")
        try:
            response = await client.post(f"{BASE_URL}/sync/all-files")
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Sync completed: {result['message']}")
            else:
                print(f"❌ Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print()
        print("=== Integration Test Complete ===")
        print("If all tests passed, the integration is working correctly!")

async def cleanup_test_data():
    """Limpia datos de test creados"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(f"{BASE_URL}/metadata/test_file.parquet")
            if response.status_code == 200:
                print("✅ Test data cleaned up")
        except Exception as e:
            print(f"Cleanup failed: {e}")

if __name__ == "__main__":
    print("Starting integration tests...")
    print("Make sure your application is running on http://localhost:8000")
    print()
    
    asyncio.run(test_integrated_endpoints())
    
    # Opcional: limpiar datos de test
    cleanup = input("\nCleanup test data? (y/n): ")
    if cleanup.lower() == 'y':
        asyncio.run(cleanup_test_data())