import pandas as pd
from data_contract_components.data_assets._query_postgres_helper import PostgresDB


def get_data_catalog() -> pd.DataFrame:
    """    
    This function queries the PostgreSQL information_schema to get detailed
    information about all columns in public tables, including their metadata
    and any associated comments.
    """
    sql = PostgresDB()
    sql_query_str = """

    -- https://www.postgresql.org/docs/17/infoschema-columns.html
    -- You can extract the schema of columns from the information_schema.columns table.
    -- Note that information_schema.columns.table_schema = 'public' provides us the tables
    -- we are focusing on the project.

    WITH columns_data AS (    
        SELECT
            information_schema.columns.table_catalog,
            information_schema.columns.table_schema,
            information_schema.columns.table_name,
            information_schema.columns.column_name,
            col_description(
                (
                    information_schema.columns.table_schema || '.' || information_schema.columns.table_name)::regclass::oid,
                    information_schema.columns.ordinal_position
                ),
            information_schema.columns.column_default,
            information_schema.columns.is_nullable,
            information_schema.columns.data_type,
            information_schema.columns.character_maximum_length,
            information_schema.columns.numeric_precision,
            information_schema.columns.datetime_precision,
            information_schema.columns.interval_type,
            information_schema.columns.udt_name,
            information_schema.columns.is_updatable,
            information_schema.columns.dtd_identifier,
            information_schema.columns.ordinal_position
        FROM
            information_schema.columns
        WHERE
            information_schema.columns.table_schema = 'public'
    ),

    -- https://www.postgresql.org/docs/17/infoschema-element-types.html
    -- Note that arrays need further analysis to extract their types. These values can be found
    -- within the information_schema.element_types table.

    element_types_data AS (
        SELECT
            information_schema.element_types.collection_type_identifier,
            information_schema.element_types.data_type AS element_data_type,
            information_schema.element_types.character_maximum_length AS element_character_maximum_length,
            information_schema.element_types.numeric_precision AS element_numeric_precision,
            information_schema.element_types.datetime_precision AS element_datetime_precision,
            information_schema.element_types.interval_type AS element_interval_type,
            information_schema.element_types.udt_name AS element_udt_name,
            information_schema.element_types.object_catalog,
            information_schema.element_types.object_schema,
            information_schema.element_types.object_name,
            information_schema.element_types.object_type
        FROM
            information_schema.element_types
        WHERE
            information_schema.element_types.object_type = 'TABLE'
    ),

    -- https://www.postgresql.org/docs/17/infoschema-constraint-column-usage.html
    -- Table to get column constraints from postgres. In this particulary case we
    -- are interested in identifying primary keys.

    table_constraints_data AS (
        SELECT 
            information_schema.constraint_column_usage.table_catalog,
            information_schema.constraint_column_usage.table_schema,
            information_schema.constraint_column_usage.table_name,
            information_schema.constraint_column_usage.column_name,
            information_schema.constraint_column_usage.constraint_name,
            information_schema.table_constraints.constraint_type
        FROM
            information_schema.constraint_column_usage
        LEFT JOIN
            information_schema.table_constraints ON
                information_schema.table_constraints.constraint_name = information_schema.constraint_column_usage.constraint_name
        WHERE
            information_schema.constraint_column_usage.table_schema = 'public'
    )

    SELECT
        columns_data.table_catalog,
        columns_data.table_schema,
        columns_data.table_name,
        columns_data.column_name,
        columns_data.col_description,
        columns_data.column_default,
        columns_data.is_nullable,
        columns_data.data_type,
        columns_data.character_maximum_length,
        columns_data.numeric_precision,
        columns_data.datetime_precision,
        columns_data.interval_type,
        columns_data.udt_name,
        columns_data.is_updatable,
        columns_data.dtd_identifier,
        element_types_data.collection_type_identifier AS element_collection_type_identifier,
        element_types_data.element_data_type,
        element_types_data.element_character_maximum_length,
        element_types_data.element_numeric_precision,
        element_types_data.element_datetime_precision,
        element_types_data.element_interval_type,
        element_types_data.element_udt_name,
        table_constraints_data.constraint_type    
    FROM
        columns_data
    LEFT JOIN
        -- Context from the postgres documentation:
        --
        --     dtd_identifier:
        --         An identifier of the data type descriptor of the column, unique among the data type descriptors
        --         pertaining to the table. This is mainly useful for joining with other instances of such identifiers.
        --
        --     collection_type_identifier:
        --         The identifier of the data type descriptor of the array being described. Use this to join with the
        --         dtd_identifier columns of other information schema views.
        element_types_data ON
            element_types_data.collection_type_identifier = columns_data.dtd_identifier AND
            element_types_data.object_catalog = columns_data.table_catalog AND
            element_types_data.object_schema = columns_data.table_schema AND
            element_types_data.object_name = columns_data.table_name
    LEFT JOIN
        table_constraints_data ON
            table_constraints_data.table_catalog = columns_data.table_catalog AND
            table_constraints_data.table_schema = columns_data.table_schema AND
            table_constraints_data.table_name = columns_data.table_name AND
            table_constraints_data.column_name = columns_data.column_name
    ORDER BY
        columns_data.table_name,
        columns_data.ordinal_position
    """

    return sql.query(sql_query_str)
