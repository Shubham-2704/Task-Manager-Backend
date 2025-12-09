from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.database import lifespan
from routes.auth_routes import router as auth_router
from routes.user_routes import router as user_router
from fastapi.staticfiles import StaticFiles


app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(user_router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {"message": "API running successfully"}
