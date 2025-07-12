from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import random
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Smart Dustbin IoT API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# IoT Models
class Location(BaseModel):
    latitude: float
    longitude: float
    address: str

class Dustbin(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    location: Location
    fill_level: float = Field(default=0, ge=0, le=100)  # 0-100%
    battery_level: float = Field(default=100, ge=0, le=100)  # 0-100%
    status: str = Field(default="online")  # online, offline, maintenance
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    is_full: bool = Field(default=False)
    temperature: float = Field(default=20.0)  # Celsius
    humidity: float = Field(default=50.0)  # Percentage

class DustbinCreate(BaseModel):
    name: str
    location: Location

class DustbinUpdate(BaseModel):
    name: Optional[str] = None
    fill_level: Optional[float] = None
    battery_level: Optional[float] = None
    status: Optional[str] = None
    is_full: Optional[bool] = None

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dustbin_id: str
    dustbin_name: str
    message: str
    type: str  # "full", "battery_low", "offline", "maintenance"
    priority: str = Field(default="medium")  # low, medium, high, critical
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)

class NotificationCreate(BaseModel):
    dustbin_id: str
    dustbin_name: str
    message: str
    type: str
    priority: str = "medium"

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Smart Dustbin IoT API", "status": "active", "bins_count": await db.dustbins.count_documents({})}

@api_router.post("/dustbins", response_model=Dustbin)
async def create_dustbin(dustbin: DustbinCreate):
    """Create a new smart dustbin"""
    dustbin_dict = dustbin.dict()
    dustbin_obj = Dustbin(**dustbin_dict)
    await db.dustbins.insert_one(dustbin_obj.dict())
    return dustbin_obj

@api_router.get("/dustbins", response_model=List[Dustbin])
async def get_dustbins():
    """Get all dustbins with current status"""
    dustbins = await db.dustbins.find().to_list(1000)
    return [Dustbin(**dustbin) for dustbin in dustbins]

@api_router.get("/dustbins/{dustbin_id}", response_model=Dustbin)
async def get_dustbin(dustbin_id: str):
    """Get specific dustbin by ID"""
    dustbin = await db.dustbins.find_one({"id": dustbin_id})
    if not dustbin:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    return Dustbin(**dustbin)

@api_router.put("/dustbins/{dustbin_id}", response_model=Dustbin)
async def update_dustbin(dustbin_id: str, update_data: DustbinUpdate):
    """Update dustbin data (IoT sensor updates)"""
    dustbin = await db.dustbins.find_one({"id": dustbin_id})
    if not dustbin:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    update_dict["last_updated"] = datetime.utcnow()
    
    # Check if bin is full and create notification
    if "fill_level" in update_dict and update_dict["fill_level"] >= 90:
        update_dict["is_full"] = True
        # Create full bin notification
        notification = NotificationCreate(
            dustbin_id=dustbin_id,
            dustbin_name=dustbin["name"],
            message=f"Dustbin '{dustbin['name']}' is {update_dict['fill_level']:.1f}% full and needs emptying!",
            type="full",
            priority="high"
        )
        await create_notification(notification)
    
    # Check battery level
    if "battery_level" in update_dict and update_dict["battery_level"] <= 20:
        notification = NotificationCreate(
            dustbin_id=dustbin_id,
            dustbin_name=dustbin["name"],
            message=f"Dustbin '{dustbin['name']}' has low battery: {update_dict['battery_level']:.1f}%",
            type="battery_low",
            priority="medium"
        )
        await create_notification(notification)
    
    await db.dustbins.update_one({"id": dustbin_id}, {"$set": update_dict})
    updated_dustbin = await db.dustbins.find_one({"id": dustbin_id})
    return Dustbin(**updated_dustbin)

@api_router.delete("/dustbins/{dustbin_id}")
async def delete_dustbin(dustbin_id: str):
    """Delete a dustbin"""
    result = await db.dustbins.delete_one({"id": dustbin_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Dustbin not found")
    return {"message": "Dustbin deleted successfully"}

@api_router.post("/notifications", response_model=Notification)
async def create_notification(notification: NotificationCreate):
    """Create a new notification"""
    notification_dict = notification.dict()
    notification_obj = Notification(**notification_dict)
    await db.notifications.insert_one(notification_obj.dict())
    return notification_obj

@api_router.get("/notifications", response_model=List[Notification])
async def get_notifications(limit: int = 50, unread_only: bool = False):
    """Get notifications"""
    query = {"is_read": False} if unread_only else {}
    notifications = await db.notifications.find(query).sort("timestamp", -1).limit(limit).to_list(limit)
    return [Notification(**notification) for notification in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark notification as read"""
    result = await db.notifications.update_one({"id": notification_id}, {"$set": {"is_read": True}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}

@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    total_bins = await db.dustbins.count_documents({})
    full_bins = await db.dustbins.count_documents({"fill_level": {"$gte": 90}})
    offline_bins = await db.dustbins.count_documents({"status": "offline"})
    low_battery_bins = await db.dustbins.count_documents({"battery_level": {"$lte": 20}})
    unread_notifications = await db.notifications.count_documents({"is_read": False})
    
    # Calculate average fill level
    pipeline = [{"$group": {"_id": None, "avg_fill": {"$avg": "$fill_level"}}}]
    avg_result = await db.dustbins.aggregate(pipeline).to_list(1)
    avg_fill_level = avg_result[0]["avg_fill"] if avg_result else 0
    
    return {
        "total_bins": total_bins,
        "full_bins": full_bins,
        "offline_bins": offline_bins,
        "low_battery_bins": low_battery_bins,
        "unread_notifications": unread_notifications,
        "avg_fill_level": round(avg_fill_level, 1),
        "last_updated": datetime.utcnow()
    }

@api_router.post("/simulate/iot-data")
async def simulate_iot_data():
    """Simulate IoT sensor data updates for all bins"""
    dustbins = await db.dustbins.find().to_list(1000)
    updates_made = 0
    
    for dustbin in dustbins:
        # Simulate realistic changes
        fill_change = random.uniform(-2, 5)  # Bins generally fill up over time
        battery_change = random.uniform(-0.5, 0.1)  # Battery slowly drains
        temp_change = random.uniform(-2, 2)  # Temperature fluctuation
        humidity_change = random.uniform(-5, 5)  # Humidity fluctuation
        
        new_fill = max(0, min(100, dustbin["fill_level"] + fill_change))
        new_battery = max(0, min(100, dustbin["battery_level"] + battery_change))
        new_temp = max(-10, min(50, dustbin["temperature"] + temp_change))
        new_humidity = max(0, min(100, dustbin["humidity"] + humidity_change))
        
        # Randomly simulate some bins going offline
        new_status = "offline" if random.random() < 0.02 else "online"
        
        update_data = DustbinUpdate(
            fill_level=new_fill,
            battery_level=new_battery,
            status=new_status,
            is_full=new_fill >= 90
        )
        
        await update_dustbin(dustbin["id"], update_data)
        
        # Update temperature and humidity manually
        await db.dustbins.update_one(
            {"id": dustbin["id"]}, 
            {"$set": {"temperature": new_temp, "humidity": new_humidity}}
        )
        updates_made += 1
    
    return {"message": f"Simulated IoT updates for {updates_made} dustbins", "timestamp": datetime.utcnow()}

@api_router.post("/initialize-demo-data")
async def initialize_demo_data():
    """Initialize demo data with realistic city locations"""
    # Clear existing data
    await db.dustbins.delete_many({})
    await db.notifications.delete_many({})
    
    # Demo locations in major cities
    demo_locations = [
        {"name": "Central Park East", "lat": 40.7829, "lng": -73.9654, "address": "Central Park East, New York, NY"},
        {"name": "Times Square", "lat": 40.7580, "lng": -73.9855, "address": "Times Square, New York, NY"},
        {"name": "Brooklyn Bridge", "lat": 40.7061, "lng": -73.9969, "address": "Brooklyn Bridge, New York, NY"},
        {"name": "Golden Gate Park", "lat": 37.7694, "lng": -122.4862, "address": "Golden Gate Park, San Francisco, CA"},
        {"name": "Fisherman's Wharf", "lat": 37.8080, "lng": -122.4177, "address": "Fisherman's Wharf, San Francisco, CA"},
        {"name": "Union Square", "lat": 37.7879, "lng": -122.4075, "address": "Union Square, San Francisco, CA"},
        {"name": "Santa Monica Pier", "lat": 34.0195, "lng": -118.4912, "address": "Santa Monica Pier, Los Angeles, CA"},
        {"name": "Hollywood Boulevard", "lat": 34.1022, "lng": -118.3390, "address": "Hollywood Boulevard, Los Angeles, CA"},
        {"name": "Venice Beach", "lat": 33.9850, "lng": -118.4695, "address": "Venice Beach, Los Angeles, CA"},
        {"name": "Navy Pier", "lat": 41.8917, "lng": -87.6086, "address": "Navy Pier, Chicago, IL"},
        {"name": "Millennium Park", "lat": 41.8826, "lng": -87.6226, "address": "Millennium Park, Chicago, IL"},
        {"name": "Lincoln Park", "lat": 41.9742, "lng": -87.6661, "address": "Lincoln Park, Chicago, IL"}
    ]
    
    created_bins = []
    for i, loc in enumerate(demo_locations):
        dustbin = DustbinCreate(
            name=f"SmartBin-{i+1:03d} ({loc['name']})",
            location=Location(
                latitude=loc["lat"],
                longitude=loc["lng"],
                address=loc["address"]
            )
        )
        
        # Create dustbin with random initial data
        dustbin_dict = dustbin.dict()
        dustbin_obj = Dustbin(**dustbin_dict)
        dustbin_obj.fill_level = random.uniform(10, 95)
        dustbin_obj.battery_level = random.uniform(30, 100)
        dustbin_obj.temperature = random.uniform(15, 35)
        dustbin_obj.humidity = random.uniform(30, 70)
        dustbin_obj.status = random.choice(["online", "online", "online", "offline"])  # 75% online
        dustbin_obj.is_full = dustbin_obj.fill_level >= 90
        
        await db.dustbins.insert_one(dustbin_obj.dict())
        created_bins.append(dustbin_obj)
    
    return {"message": f"Initialized {len(created_bins)} demo dustbins", "bins": len(created_bins)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Background task for IoT simulation
@app.on_event("startup")
async def startup_event():
    logger.info("Smart Dustbin IoT API started successfully")