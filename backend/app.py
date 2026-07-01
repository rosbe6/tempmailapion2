from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import threading
import time

import database
import mail_monitor

app = FastAPI(title="Tempmail API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_connections = []

# ============= WEBSOCKET =============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except:
        if websocket in active_connections:
            active_connections.remove(websocket)

# ============= RUTAS API =============

from pydantic import BaseModel

class AddressRequest(BaseModel):
    name: str

@app.post("/api/address/generate")
async def generate_address(request: AddressRequest):
    """Genera una dirección temporal con nombre personalizado"""
    if not request.name or len(request.name) < 3:
        raise HTTPException(status_code=400, detail="El nombre debe tener al menos 3 caracteres")
    
    result = database.generate_temp_address(request.name)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result

@app.get("/api/address/{address_id}")
async def get_address(address_id: str):
    """Obtiene info de una dirección"""
    address = database.get_temp_address(address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Dirección no encontrada")
    return address

@app.get("/api/emails/{address_id}")
async def get_emails(address_id: str):
    """Obtiene todos los correos de una dirección"""
    emails = database.get_emails_by_address(address_id)
    return {"emails": emails}

@app.get("/api/emails/detail/{email_id}")
async def get_email(email_id: int):
    """Obtiene un correo específico"""
    email = database.get_email_by_id(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    database.mark_email_as_read(email_id)
    return email

@app.post("/api/emails/{email_id}/delete")
async def delete_email(email_id: int):
    """Elimina un correo"""
    database.delete_email(email_id)
    return {"status": "deleted"}

@app.post("/api/emails/{address_id}/clear")
async def clear_emails(address_id: str):
    """Limpia todos los correos de una dirección"""
    database.clear_emails_by_address(address_id)
    return {"status": "cleared"}

@app.post("/api/sync")
async def sync_emails():
    """Sincroniza correos"""
    try:
        new_count = mail_monitor.import_new_emails()
        return {"new_emails": new_count, "status": "synced"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def serve_frontend():
    """Sirve el dashboard"""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Frontend not found"}

# ============= BACKGROUND TASK =============

def background_mail_sync():
    while True:
        try:
            new_count = mail_monitor.import_new_emails()
            if new_count > 0:
                print(f"[SYNC] {new_count} correo(s) nuevo(s)")
        except Exception as e:
            print(f"[SYNC ERROR] {e}")
        time.sleep(10)

sync_thread = threading.Thread(target=background_mail_sync, daemon=True)
sync_thread.start()

@app.on_event("startup")
async def startup():
    print("=" * 50)
    print("✓ Tempmail API iniciada")
    print("✓ Base de datos lista")
    print("=" * 50)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)