import asyncpg
from typing import Optional, List
from interfaces import Lead, LeadState
from datetime import datetime

async def create_pool(db_url: str):
    return await asyncpg.create_pool(
        dsn=db_url,
        min_size=2,
        max_size=5,
        max_inactive_connection_lifetime=300
    )

async def create_tables(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                resume_s3_key TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_leads_state ON leads(state);
            CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);
        """)


async def insert_lead(pool: asyncpg.Pool, lead: Lead) -> bool:
    try:
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO leads (id, first_name, last_name, email, resume_s3_key, state, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, lead.id, lead.first_name, lead.last_name, lead.email, 
            lead.resume_s3_key, lead.state.value, lead.created_at, lead.updated_at)
        return True
    except Exception as e:
        print(f"Error inserting lead: {e}")
        return False


async def get_leads(
    pool: asyncpg.Pool,
    skip: int = 0,
    limit: int = 10,
    state: Optional[LeadState] = None
) -> tuple[List[Lead], int]:
    async with pool.acquire() as conn:
        # Build query based on filter
        if state:
            query = """
                SELECT id, first_name, last_name, email, resume_s3_key, state, created_at, updated_at
                FROM leads
                WHERE state = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
            """
            count_query = "SELECT COUNT(*) FROM leads WHERE state = $1"
            rows = await conn.fetch(query, state.value, limit, skip)
            count = await conn.fetchval(count_query, state.value)
        else:
            query = """
                SELECT id, first_name, last_name, email, resume_s3_key, state, created_at, updated_at
                FROM leads
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            count_query = "SELECT COUNT(*) FROM leads"
            rows = await conn.fetch(query, limit, skip)
            count = await conn.fetchval(count_query)
        
        leads = [
            Lead(
                id=row['id'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                email=row['email'],
                resume_s3_key=row['resume_s3_key'],
                state=LeadState(row['state']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]
        
        return leads, count


async def update_lead_state(pool: asyncpg.Pool, lead_id: str, new_state: LeadState) -> Optional[Lead]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE leads
            SET state = $1, updated_at = $2
            WHERE id = $3
            RETURNING id, first_name, last_name, email, resume_s3_key, state, created_at, updated_at
        """, new_state.value, datetime.utcnow(), lead_id)
        
        if row:
            return Lead(
                id=row['id'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                email=row['email'],
                resume_s3_key=row['resume_s3_key'],
                state=LeadState(row['state']),
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
        return None
