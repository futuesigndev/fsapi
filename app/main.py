from fastapi import FastAPI  # ตรวจสอบว่า import FastAPI

from app.api.routes import router  # ตรวจสอบว่ามีการนำเข้า router

app = FastAPI()

# รวมเส้นทาง API
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
