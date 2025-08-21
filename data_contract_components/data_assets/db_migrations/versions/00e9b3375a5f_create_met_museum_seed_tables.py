"""create met museum seed tables

Revision ID: 00e9b3375a5f
Revises: 
Create Date: 2025-08-06 04:03:44.279544+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSON


# revision identifiers, used by Alembic.
revision: str = '00e9b3375a5f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

column_comment_dict: dict[str, str] = {
    "object_id": (
        "Identifying number for each artwork (unique, can be used as key "
        "field); Example: 437133"
    ),
    "artist_display_name": (
        "Artist name in the correct order for display; "
        'Example: "Vincent van Gogh"'
    ),
    "title": (
        "Title, identifying phrase, or name given to a work of art; "
        'Example: "Wheat Field with Cypresses"'
    ),
    "period": (
        "Time or time period when an object was created; "
        'Example: "Ming dynasty (1368-1644)"'
    ),
    "culture": (
        "Information about the culture or people from which an object was "
        'created; Example: "Afghan"'
    ),
    "object_date": (
        "Year, span of years, or phrase describing when the artwork was "
        'designed or created; Example: "19th century"'
    ),
    "medium": (
        "Materials used to create the artwork; "
        'Example: "Oil on canvas"'
    ),
    "dimensions": (
        "Physical size of the artwork or object; "
        'Example: "16 x 20 in. (40.6 x 50.8 cm)"'
    ),
    "classification": (
        "General term describing the artwork type; "
        'Example: "Paintings"'
    ),
    "gallery_number": (
        "Gallery number (when available) where the object is displayed; "
        'Example: "131"'
    ),
    "department": (
        "Met curatorial department responsible for the artwork; "
        'Example: "Egyptian Art"'
    ),
    "accession_number": (
        "Museum accession number (not always unique); "
        'Example: "67.241"'
    ),
    "tags": (
        "JSON array of subject keyword tags associated with the object and "
        "their controlled-vocabulary URLs; "
        'Example element: {"term": "Abstraction", "AAT_URL": "..."}'
    ),
    "primary_image": (
        "URL to the primary image of an object (JPEG); "
        'Example: "https://images.metmuseum.org/.../DT1567.jpg"'
    ),
    "additional_images": (
        "Array of URLs to additional JPEG images of the object; "
        'Example: ["https://images.metmuseum.org/..._001.jpg", "..."]'
    ),
    "is_public_domain": (
        'Boolean flag indicating whether the artwork is in the public domain; '
        'Example: true'
    ),
    "metadata_date": (
        "Timestamp when the object metadata was last updated; "
        'Example: 2018-10-17T10:24:43.197Z'
    ),
    "created_at": (
        "Timestamp when this record was created in the database; "
        'Example: 2025-01-15T10:30:00.000Z'
    ),
}


def upgrade() -> None:
    op.create_table(
        "object",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "title",
            sa.Text,
            comment=column_comment_dict["title"]
        ),
        sa.Column(
            "artist_display_name",
            sa.Text,
            comment=column_comment_dict["artist_display_name"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )

    op.create_table(
        "object_history",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "period",
            sa.Text,
            comment=column_comment_dict["period"]
        ),
        sa.Column(
            "culture",
            sa.Text,
            comment=column_comment_dict["culture"]
        ),
        sa.Column(
            "object_date",
            sa.Text,
            comment=column_comment_dict["object_date"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )

    op.create_table(
        "object_physical_properties",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "medium",
            sa.Text,
            comment=column_comment_dict["medium"]
        ),
        sa.Column(
            "dimensions",
            sa.Text,
            comment=column_comment_dict["dimensions"]
        ),
        sa.Column(
            "classification",
            sa.Text,
            comment=column_comment_dict["classification"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )

    op.create_table(
        "object_gallery_info",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "gallery_number",
            sa.Text,
            comment=column_comment_dict["gallery_number"]
        ),
        sa.Column(
            "department",
            sa.Text,
            comment=column_comment_dict["department"]
        ),
        sa.Column(
            "accession_number",
            sa.Text,
            comment=column_comment_dict["accession_number"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )

    op.create_table(
        "object_tags",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "tags",
            ARRAY(JSON),
            comment=column_comment_dict["tags"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )

    op.create_table(
        "object_images",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "primary_image",
            sa.Text,
            comment=column_comment_dict["primary_image"]
        ),
        sa.Column(
            "additional_images",
            ARRAY(sa.Text),
            comment=column_comment_dict["additional_images"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )

    op.create_table(
        "object_copyright",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "primary_image",
            sa.Text,
            comment=column_comment_dict["primary_image"]
        ),
        sa.Column(
            "is_public_domain",
            sa.Boolean,
            comment=column_comment_dict["is_public_domain"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )

    op.create_table(
        "object_api_metadata",
        sa.Column(
            "object_id",
            sa.Integer,
            primary_key=True,
            comment=column_comment_dict["object_id"]
        ),
        sa.Column(
            "metadata_date",
            sa.DateTime,
            comment=column_comment_dict["metadata_date"]
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment=column_comment_dict["created_at"]
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("object")
    op.drop_table("object_history")
    op.drop_table("object_physical_properties")
    op.drop_table("object_gallery_info")
    op.drop_table("object_tags")
    op.drop_table("object_images")
    op.drop_table("object_copyright")
    op.drop_table("object_api_metadata")
