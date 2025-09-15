from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from config import settings

security = HTTPBasic()

def verify_admin_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Verifica las credenciales del administrador
    Returns: username del admin autenticado
    """
    username = credentials.username
    password = credentials.password
    
    # Verificar si el usuario existe en la configuración
    if username not in settings.ADMIN_USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autorizado",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Verificar contraseña usando comparación segura
    expected_password = settings.ADMIN_USERS[username]
    is_correct_password = secrets.compare_digest(password, expected_password)
    
    if not is_correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return username