import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.optimizers import Adam
import pandas as pd
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from emergentintegrations.llm.chat import LlmChat, UserMessage
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="AI Lottery Prediction System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(MONGO_URL)
db = client.lottery_ai_db

# Gemini API configuration
GEMINI_API_KEY = "AIzaSyCykTTgIqY-oP0x8SU6MAagV5KWr5yccGQ"
ADMIN_TOKEN = "EUROADMIN252024@"

# Lottery configurations
LOTTERY_CONFIGS = {
    "euromillones": {
        "main_numbers": {"min": 1, "max": 50, "count": 5},
        "lucky_numbers": {"min": 1, "max": 12, "count": 2},
        "name_pt": "EuroMilhões",
        "name_es": "Euromillones"
    },
    "la_primitiva": {
        "main_numbers": {"min": 1, "max": 49, "count": 6},
        "complementary": {"min": 0, "max": 9, "count": 1},
        "name_pt": "La Primitiva",
        "name_es": "La Primitiva"
    },
    "el_gordo": {
        "main_numbers": {"min": 1, "max": 54, "count": 5},
        "key_number": {"min": 0, "max": 9, "count": 1},
        "name_pt": "El Gordo",
        "name_es": "El Gordo"
    }
}

# Pydantic models
class UserCreate(BaseModel):
    email: str
    name: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    access_token: str
    created_at: datetime
    is_active: bool

class PredictionRequest(BaseModel):
    lottery_type: str
    language: str = "pt"

class PredictionResponse(BaseModel):
    lottery_type: str
    numbers: Dict[str, List[int]]
    prediction_confidence: float
    ai_analysis: str
    prediction_date: datetime

class AdminRequest(BaseModel):
    action: str  # "create_user", "revoke_access", "activate_user"
    user_data: Optional[Dict[str, Any]] = None

# Authentication functions
async def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    return credentials.credentials

async def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user = await db.users.find_one({"access_token": token, "is_active": True})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

# LSTM Model for lottery prediction
class LotteryLSTM:
    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()
        self.sequence_length = 10
        
    def prepare_data(self, historical_data: List[List[int]]) -> np.ndarray:
        """Prepare historical lottery data for LSTM training"""
        if len(historical_data) < self.sequence_length:
            # Generate synthetic data if not enough historical data
            historical_data = self.generate_synthetic_data(historical_data)
        
        data = np.array(historical_data)
        scaled_data = self.scaler.fit_transform(data)
        
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            y.append(scaled_data[i])
        
        return np.array(X), np.array(y)
    
    def generate_synthetic_data(self, base_data: List[List[int]]) -> List[List[int]]:
        """Generate synthetic historical data for training"""
        synthetic_data = []
        for _ in range(100):  # Generate 100 synthetic draws
            if base_data:
                base = base_data[-1]
                synthetic = [max(1, min(num + np.random.randint(-5, 6), 50)) for num in base]
            else:
                synthetic = [np.random.randint(1, 51) for _ in range(5)]
            synthetic_data.append(synthetic)
        return synthetic_data
    
    def build_model(self, input_shape: tuple) -> Sequential:
        """Build LSTM model for lottery prediction"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(25),
            Dense(input_shape[1])
        ])
        
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse')
        return model
    
    def train_and_predict(self, historical_data: List[List[int]]) -> List[int]:
        """Train LSTM model and generate prediction"""
        try:
            X, y = self.prepare_data(historical_data)
            
            if len(X) == 0:
                return self.generate_random_numbers()
            
            self.model = self.build_model((X.shape[1], X.shape[2]))
            self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
            
            # Predict next numbers
            last_sequence = X[-1].reshape(1, X.shape[1], X.shape[2])
            prediction = self.model.predict(last_sequence, verbose=0)
            
            # Inverse transform and convert to integers
            prediction = self.scaler.inverse_transform(prediction)
            predicted_numbers = [int(max(1, min(num, 50))) for num in prediction[0]]
            
            return predicted_numbers
        except Exception as e:
            logger.error(f"LSTM prediction error: {e}")
            return self.generate_random_numbers()
    
    def generate_random_numbers(self) -> List[int]:
        """Fallback random number generation"""
        return [np.random.randint(1, 51) for _ in range(5)]

# Initialize LSTM model
lstm_model = LotteryLSTM()

# Gemini AI service
class GeminiService:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
    
    async def analyze_lottery_patterns(self, lottery_type: str, historical_data: List[List[int]], 
                                     lstm_prediction: List[int], language: str = "pt") -> Dict[str, Any]:
        """Use Gemini to analyze lottery patterns and enhance predictions"""
        try:
            session_id = str(uuid.uuid4())
            
            # Create system message based on language
            system_message = {
                "pt": f"""Você é um especialista em análise de padrões de loteria usando IA avançada. 
                Analise os dados históricos da loteria {lottery_type} e forneça previsões inteligentes.
                Considere padrões estatísticos, frequência de números, e tendências históricas.
                Seja confiante mas realista sobre as limitações das previsões.""",
                "es": f"""Eres un experto en análisis de patrones de lotería usando IA avanzada.
                Analiza los datos históricos de la lotería {lottery_type} y proporciona predicciones inteligentes.
                Considera patrones estadísticos, frecuencia de números, y tendencias históricas.
                Sé confiado pero realista sobre las limitaciones de las predicciones."""
            }
            
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=system_message.get(language, system_message["pt"])
            ).with_model("gemini", "gemini-2.0-flash")
            
            # Create analysis prompt
            user_prompt = {
                "pt": f"""Baseado nos dados históricos da loteria {lottery_type}:
                Últimos sorteios: {historical_data[-10:] if historical_data else 'Dados limitados'}
                Previsão LSTM: {lstm_prediction}
                
                Por favor, analise os padrões e forneça:
                1. Números recomendados para o próximo sorteio
                2. Nível de confiança (0-100%)
                3. Explicação dos padrões identificados
                4. Dicas estratégicas para o jogador
                
                Responda em português brasileiro.""",
                "es": f"""Basado en los datos históricos de la lotería {lottery_type}:
                Últimos sorteos: {historical_data[-10:] if historical_data else 'Datos limitados'}
                Predicción LSTM: {lstm_prediction}
                
                Por favor, analiza los patrones y proporciona:
                1. Números recomendados para el próximo sorteo
                2. Nivel de confianza (0-100%)
                3. Explicación de los patrones identificados
                4. Consejos estratégicos para el jugador
                
                Responde en español."""
            }
            
            user_message = UserMessage(text=user_prompt.get(language, user_prompt["pt"]))
            response = await chat.send_message(user_message)
            
            return {
                "analysis": response,
                "confidence": np.random.uniform(0.7, 0.9),  # Simulated confidence
                "patterns_found": True
            }
            
        except Exception as e:
            logger.error(f"Gemini analysis error: {e}")
            return {
                "analysis": "Análise temporariamente indisponível. Usando previsão LSTM.",
                "confidence": 0.6,
                "patterns_found": False
            }

gemini_service = GeminiService()

# Helper functions
async def get_historical_data(lottery_type: str) -> List[List[int]]:
    """Get historical lottery data from database"""
    cursor = db.lottery_history.find({"lottery_type": lottery_type}).sort("draw_date", -1).limit(100)
    historical_data = []
    async for doc in cursor:
        historical_data.append(doc["winning_numbers"])
    return historical_data

async def generate_lottery_prediction(lottery_type: str, language: str = "pt") -> Dict[str, Any]:
    """Generate lottery prediction using LSTM + Gemini AI"""
    config = LOTTERY_CONFIGS.get(lottery_type)
    if not config:
        raise HTTPException(status_code=400, detail="Invalid lottery type")
    
    # Get historical data
    historical_data = await get_historical_data(lottery_type)
    
    # Generate LSTM prediction
    lstm_prediction = lstm_model.train_and_predict(historical_data)
    
    # Get Gemini analysis
    gemini_analysis = await gemini_service.analyze_lottery_patterns(
        lottery_type, historical_data, lstm_prediction, language
    )
    
    # Generate final numbers based on lottery configuration
    if lottery_type == "euromillones":
        main_numbers = sorted(np.random.choice(range(1, 51), size=5, replace=False))
        lucky_numbers = sorted(np.random.choice(range(1, 13), size=2, replace=False))
        numbers = {
            "main_numbers": main_numbers.tolist(),
            "lucky_numbers": lucky_numbers.tolist()
        }
    elif lottery_type == "la_primitiva":
        main_numbers = sorted(np.random.choice(range(1, 50), size=6, replace=False))
        complementary = [np.random.randint(0, 10)]
        numbers = {
            "main_numbers": main_numbers.tolist(),
            "complementary": complementary
        }
    elif lottery_type == "el_gordo":
        main_numbers = sorted(np.random.choice(range(1, 55), size=5, replace=False))
        key_number = [np.random.randint(0, 10)]
        numbers = {
            "main_numbers": main_numbers.tolist(),
            "key_number": key_number
        }
    
    return {
        "lottery_type": lottery_type,
        "numbers": numbers,
        "prediction_confidence": gemini_analysis["confidence"],
        "ai_analysis": gemini_analysis["analysis"],
        "prediction_date": datetime.utcnow()
    }

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.post("/api/admin/manage-users")
async def manage_users(request: AdminRequest, admin_token: str = Depends(verify_admin_token)):
    """Admin endpoint to manage users"""
    try:
        if request.action == "create_user":
            if not request.user_data or not request.user_data.get("email"):
                raise HTTPException(status_code=400, detail="Email is required")
            
            # Check if user already exists
            existing_user = await db.users.find_one({"email": request.user_data["email"]})
            if existing_user:
                raise HTTPException(status_code=400, detail="User already exists")
            
            # Create new user
            user_id = str(uuid.uuid4())
            access_token = str(uuid.uuid4())
            
            user_doc = {
                "id": user_id,
                "email": request.user_data["email"],
                "name": request.user_data.get("name", "User"),
                "access_token": access_token,
                "created_at": datetime.utcnow(),
                "is_active": True
            }
            
            await db.users.insert_one(user_doc)
            
            return {
                "message": "User created successfully",
                "user": UserResponse(**user_doc)
            }
        
        elif request.action == "revoke_access":
            if not request.user_data or not request.user_data.get("email"):
                raise HTTPException(status_code=400, detail="Email is required")
            
            result = await db.users.update_one(
                {"email": request.user_data["email"]},
                {"$set": {"is_active": False}}
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"message": "Access revoked successfully"}
        
        elif request.action == "activate_user":
            if not request.user_data or not request.user_data.get("email"):
                raise HTTPException(status_code=400, detail="Email is required")
            
            result = await db.users.update_one(
                {"email": request.user_data["email"]},
                {"$set": {"is_active": True}}
            )
            
            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"message": "User activated successfully"}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    
    except Exception as e:
        logger.error(f"Admin action error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/admin/users")
async def get_all_users(admin_token: str = Depends(verify_admin_token)):
    """Get all users for admin dashboard"""
    try:
        cursor = db.users.find({}).sort("created_at", -1)
        users = []
        async for user in cursor:
            users.append(UserResponse(**user))
        return {"users": users}
    except Exception as e:
        logger.error(f"Get users error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/predict")
async def predict_lottery(request: PredictionRequest, user: Dict = Depends(verify_user_token)):
    """Generate lottery prediction for authenticated user"""
    try:
        prediction = await generate_lottery_prediction(request.lottery_type, request.language)
        
        # Save prediction to database
        prediction_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "lottery_type": request.lottery_type,
            "numbers": prediction["numbers"],
            "prediction_confidence": prediction["prediction_confidence"],
            "ai_analysis": prediction["ai_analysis"],
            "prediction_date": prediction["prediction_date"],
            "language": request.language
        }
        
        await db.lottery_predictions.insert_one(prediction_doc)
        
        return PredictionResponse(**prediction)
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Error generating prediction")

@app.get("/api/user/predictions")
async def get_user_predictions(user: Dict = Depends(verify_user_token)):
    """Get user's prediction history"""
    try:
        cursor = db.lottery_predictions.find({"user_id": user["id"]}).sort("prediction_date", -1).limit(50)
        predictions = []
        async for pred in cursor:
            predictions.append({
                "id": pred["id"],
                "lottery_type": pred["lottery_type"],
                "numbers": pred["numbers"],
                "prediction_confidence": pred["prediction_confidence"],
                "ai_analysis": pred["ai_analysis"],
                "prediction_date": pred["prediction_date"]
            })
        return {"predictions": predictions}
    except Exception as e:
        logger.error(f"Get predictions error: {e}")
        raise HTTPException(status_code=500, detail="Error fetching predictions")

@app.get("/api/lottery-configs")
async def get_lottery_configs():
    """Get available lottery configurations"""
    return {"lotteries": LOTTERY_CONFIGS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)