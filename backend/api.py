import os
from dotenv import load_dotenv 

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Depends, BackgroundTasks
from datetime import datetime
import uuid
from typing import Optional

from interfaces import Lead, LeadState, LeadStateUpdate, LeadListResponse
import db
from s3_utils import upload_resume_to_s3
from email_utils import send_lead_notifications
from auth import verify_token

load_dotenv()

app = FastAPI(
    title="Alma Leads Management API",
    version="1.0.0"
)

DATABASE_URL = os.getenv("DATABASE_URL")

@app.on_event("startup")
async def startup():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set in .env")
    app.state.db_pool = await db.create_pool(DATABASE_URL)
    await db.create_tables(app.state.db_pool)

@app.on_event("shutdown")
async def shutdown():
    await app.state.db_pool.close()

@app.post("/leads", response_model=Lead, tags=["Leads"])
async def create_lead(
    background_tasks: BackgroundTasks,
    first_name: str = Form(..., min_length=1, max_length=100),
    last_name: str = Form(..., min_length=1, max_length=100),
    email: str = Form(...),
    resume: UploadFile = File(...)
):
    allowed_types = ['application/pdf', 'application/msword', 
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if resume.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type.")
    
    lead_id = f"lead_{last_name}_{uuid.uuid4().hex[:4]}"
    
    try:
        s3_key = await upload_resume_to_s3(lead_id, resume)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")
    
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
        raise HTTPException(status_code=500, detail="Failed to save lead to database")
    
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    
    background_tasks.add_task(
        send_lead_notifications,
        prospect_email=email,
        first_name=first_name,
        admin_email=admin_email,
        lead_data={
            'id': lead_id,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'created_at': now.isoformat()
        }
    )
    
    return lead


@app.get("/leads", response_model=LeadListResponse, tags=["Leads"])
async def list_leads(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, gt=0, le=100, description="Maximum number of records to return"),
    state: Optional[LeadState] = Query(None, description="Filter by lead state"),
    _: bool = Depends(verify_token)
):
    """
    List leads with optional state filter and pagination (protected endpoint).
    
    Requires Bearer token authentication.
    """
    leads, total = await db.get_leads(app.state.db_pool, skip, limit, state)
    
    return LeadListResponse(
        leads=leads,
        total=total,
        skip=skip,
        limit=limit
    )


@app.patch("/leads/{lead_id}/state", response_model=Lead, tags=["Leads"])
async def update_state(
    lead_id: str,
    state_update: LeadStateUpdate,
    _: bool = Depends(verify_token)
):
    """
    Update the state of a lead (protected endpoint).
    
    Requires Bearer token authentication.
    """
    lead = await update_lead_state(app.state.db_pool, lead_id, state_update.state)
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return lead