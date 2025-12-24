import os
import logging
from dotenv import load_dotenv 
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends, BackgroundTasks
from datetime import datetime
import uuid
from typing import Optional

from interfaces import Lead, LeadState, LeadStateUpdate, LeadListResponse
import db
from s3_utils import upload_resume_to_s3
from auth import verify_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("api")

load_dotenv()
app = FastAPI(title="Alma Leads Management API", version="1.0.0")

DATABASE_URL = os.getenv("DATABASE_URL")

@app.on_event("startup")
async def startup():
    if not DATABASE_URL:
        logger.error("DATABASE_URL not found in environment variables.")
        raise RuntimeError("DATABASE_URL is not set in .env")
    app.state.db_pool = await db.create_pool(DATABASE_URL)
    await db.create_tables(app.state.db_pool)
    logger.info("Application started and DB pool created.")

@app.on_event("shutdown")
async def shutdown():
    await app.state.db_pool.close()
    logger.info("DB pool closed.")

@app.post("/leads", response_model=Lead, tags=["Leads"])
async def create_lead(
    background_tasks: BackgroundTasks,
    first_name: str = Form(..., min_length=1, max_length=100),
    last_name: str = Form(..., min_length=1, max_length=100),
    email: str = Form(...),
    resume: UploadFile = File(...)
):
    logger.info(f"Received lead submission for: {email}")
    
    allowed_types = ['application/pdf', 'application/msword', 
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    
    if resume.content_type not in allowed_types:
        logger.warning(f"Rejected lead {email}: Invalid file type {resume.content_type}")
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    lead_id = f"lead_{last_name.lower()}_{uuid.uuid4().hex[:4]}"
    
    try:
        s3_key = await upload_resume_to_s3(lead_id, resume)
    except Exception as e:
        logger.error(f"S3 Upload failed for {lead_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload resume.")
    
    now = datetime.utcnow()
    lead = Lead(
        id=lead_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        resume_s3_key=s3_key,
        state=LeadState.PENDING,
        created_at=now,
        updated_at=now
    )
    
    success = await db.insert_lead(app.state.db_pool, lead)
    if not success:
        logger.error(f"Database insertion failed for lead {lead_id}")
        raise HTTPException(status_code=500, detail="Failed to save lead to database")
    
    logger.info(f"Lead {lead_id} successfully created.")
    return lead

@app.patch("/leads/{lead_id}/state", response_model=Lead, tags=["Leads"])
async def update_state(
    lead_id: str,
    state_update: LeadStateUpdate,
    _: bool = Depends(verify_token)
):
    lead = await db.update_lead_state(app.state.db_pool, lead_id, state_update.state)
    
    if not lead:
        logger.warning(f"Attempted to update non-existent lead: {lead_id}")
        raise HTTPException(status_code=404, detail="Lead not found")
    
    logger.info(f"Lead {lead_id} updated to state {state_update.state}")
    return lead