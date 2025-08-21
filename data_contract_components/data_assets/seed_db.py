#!/usr/bin/env python3
"""
Seed Met Museum data into PostgreSQL using psycopg3.

This script reads the objects.json file and seeds the data into normalized PostgreSQL tables
as defined in the initial alembic migration 00e9b3375a5f_create_met_museum_raw_table.py.
"""

import json
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
import psycopg
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

# Configure logging
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Database configuration - use connection string instead of dict
DB_CONFIG = "postgresql://postgres:postgres@postgres:5432/postgres"

# Connection pool configuration
POOL_CONFIG = {
    "min_size": 1,
    "max_size": 10,
    "timeout": 30,
}

def clear_all_tables(conn: psycopg.Connection) -> None:
    """Clear all data from the initial db tables."""
    
    tables = [
        "object",
        "object_history", 
        "object_physical_properties",
        "object_gallery_info",
        "object_tags",
        "object_images",
        "object_copyright",
        "object_api_metadata"
    ]
    
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"DELETE FROM {table}")
    conn.commit()
    logger.info("Cleared all data from normalized tables")

def extract_object_data(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and clean data from a Met object record for normalized tables."""
    
    # Parse metadata_date if it exists
    metadata_date = None
    if obj.get("metadataDate"):
        try:
            metadata_date = datetime.fromisoformat(obj["metadataDate"].replace("Z", "+00:00"))
        except (ValueError, TypeError):
            metadata_date = None
    
    return {
        "object_id": obj.get("objectID"),
        "title": obj.get("title"),
        "artist_display_name": obj.get("artistDisplayName"),
        "period": obj.get("period"),
        "culture": obj.get("culture"),
        "object_date": obj.get("objectDate"),
        "medium": obj.get("medium"),
        "dimensions": obj.get("dimensions"),
        "classification": obj.get("classification"),
        "gallery_number": obj.get("galleryNumber"),
        "department": obj.get("department"),
        "accession_number": obj.get("accessionNumber"),
        "tags": obj.get("tags"),
        "primary_image": obj.get("primaryImage"),
        "additional_images": obj.get("additionalImages"),
        "is_public_domain": obj.get("isPublicDomain", False),
        "metadata_date": metadata_date
    }

def insert_object_main(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert main object data."""
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object (object_id, title, artist_display_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                title = EXCLUDED.title,
                artist_display_name = EXCLUDED.artist_display_name
        """, (data["object_id"], data["title"], data["artist_display_name"]))

def insert_object_history(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert object history data."""
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object_history (object_id, period, culture, object_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                period = EXCLUDED.period,
                culture = EXCLUDED.culture,
                object_date = EXCLUDED.object_date
        """, (data["object_id"], data["period"], data["culture"], data["object_date"]))

def insert_object_physical_properties(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert object physical properties data."""
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object_physical_properties (object_id, medium, dimensions, classification)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                medium = EXCLUDED.medium,
                dimensions = EXCLUDED.dimensions,
                classification = EXCLUDED.classification
        """, (data["object_id"], data["medium"], data["dimensions"], data["classification"]))

def insert_object_gallery_info(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert object gallery information data."""
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object_gallery_info (object_id, gallery_number, department, accession_number)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                gallery_number = EXCLUDED.gallery_number,
                department = EXCLUDED.department,
                accession_number = EXCLUDED.accession_number
        """, (data["object_id"], data["gallery_number"], data["department"], data["accession_number"]))

def insert_object_tags(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert object tags data."""
    
    # Get tags with fallback to empty list, then adapt each dict
    tags = data.get("tags") or []
    adapted_tags = [Json(tag) for tag in tags]
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object_tags (object_id, tags)
            VALUES (%s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                tags = EXCLUDED.tags
        """, (data["object_id"], adapted_tags))

def insert_object_images(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert object images data."""
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object_images (object_id, primary_image, additional_images)
            VALUES (%s, %s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                primary_image = EXCLUDED.primary_image,
                additional_images = EXCLUDED.additional_images
        """, (data["object_id"], data["primary_image"], data["additional_images"]))

def insert_object_copyright(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert object copyright data."""
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object_copyright (object_id, primary_image, is_public_domain)
            VALUES (%s, %s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                primary_image = EXCLUDED.primary_image,
                is_public_domain = EXCLUDED.is_public_domain
        """, (data["object_id"], data["primary_image"], data["is_public_domain"]))

def insert_object_api_metadata(conn: psycopg.Connection, data: Dict[str, Any]) -> None:
    """Insert object API metadata."""
    
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO object_api_metadata (object_id, metadata_date)
            VALUES (%s, %s)
            ON CONFLICT (object_id) DO UPDATE SET
                metadata_date = EXCLUDED.metadata_date
        """, (data["object_id"], data["metadata_date"]))

def insert_object_batch(conn: psycopg.Connection, objects: List[Dict[str, Any]]) -> int:
    """Insert a batch of objects into all normalized tables."""
    
    if not objects:
        return 0
    
    inserted_count = 0
    
    for obj in objects:
        try:
            data = extract_object_data(obj)
            
            # Skip if no object_id
            if not data["object_id"]:
                continue
            
            # Insert into all normalized tables
            insert_object_main(conn, data)
            insert_object_history(conn, data)
            insert_object_physical_properties(conn, data)
            insert_object_gallery_info(conn, data)
            insert_object_tags(conn, data)
            insert_object_images(conn, data)
            insert_object_copyright(conn, data)
            insert_object_api_metadata(conn, data)
            
            inserted_count += 1
            
        except Exception as e:
            logger.error(f"Error inserting object {data.get('object_id', 'unknown')}: {e}")
            continue
    
    conn.commit()
    return inserted_count

def load_and_insert_data(json_file_path: str, batch_size: int = 1000) -> None:
    """Load data from JSON file and insert into normalized database tables."""
    
    logger.info(f"Loading data from {json_file_path}")
    
    # Check if file exists
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"JSON file not found: {json_file_path}")
    
    # Create connection pool
    with ConnectionPool(conninfo=DB_CONFIG, **POOL_CONFIG) as pool:
        with pool.connection() as conn:
            # Clear existing data
            clear_all_tables(conn)
            
            # Load and process data
            with open(json_file_path, 'r', encoding='utf-8') as f:
                objects = json.load(f)
            
            logger.info(f"Loaded {len(objects)} objects from JSON file")
            
            # Process in batches
            total_inserted = 0
            for i in range(0, len(objects), batch_size):
                batch = objects[i:i + batch_size]
                
                try:
                    inserted = insert_object_batch(conn, batch)
                    total_inserted += inserted
                    logger.info(f"Inserted batch {i//batch_size + 1}: {inserted} objects")
                except Exception as e:
                    logger.error(f"Error inserting batch {i//batch_size + 1}: {e}")
                    conn.rollback()
                    raise
            
            logger.info(f"Successfully inserted {total_inserted} objects into normalized tables")

def main():
    """Main function to run the data seeding."""
    
    json_file_path = "db_migrations/raw_data/objects.json"
    
    try:
        load_and_insert_data(json_file_path)
        logger.info("Data seeding completed successfully!")
        
        # Print some statistics
        with ConnectionPool(conninfo=DB_CONFIG, **POOL_CONFIG) as pool:
            with pool.connection() as conn:
                with conn.cursor() as cur:
                    # Count objects in main table
                    cur.execute("SELECT COUNT(*) FROM object")
                    total_count = cur.fetchone()[0]
                    
                    # Count public domain objects
                    cur.execute("SELECT COUNT(*) FROM object_copyright WHERE is_public_domain = true")
                    public_domain_count = cur.fetchone()[0]
                    
                    # Top departments
                    cur.execute("""
                        SELECT department, COUNT(*) 
                        FROM object_gallery_info 
                        WHERE department IS NOT NULL 
                        GROUP BY department 
                        ORDER BY COUNT(*) DESC 
                        LIMIT 5
                    """)
                    top_departments = cur.fetchall()
                    
                    # Objects with images
                    cur.execute("SELECT COUNT(*) FROM object_images WHERE primary_image IS NOT NULL")
                    objects_with_images = cur.fetchone()[0]
                    
                    logger.info(f"Database statistics:")
                    logger.info(f"  Total objects: {total_count}")
                    logger.info(f"  Public domain objects: {public_domain_count}")
                    logger.info(f"  Objects with images: {objects_with_images}")
                    logger.info(f"  Top departments:")
                    for dept, count in top_departments:
                        logger.info(f"    {dept}: {count}")
                        
    except Exception as e:
        logger.error(f"Error during data seeding: {e}")
        raise

if __name__ == "__main__":
    main()
