def create_schema_string(df, table_name):
    """
    Generates a JSON-like string representing the DataFrame schema.

    Args:
        df (pd.DataFrame): Input DataFrame.
        table_name (str): Name of the table.

    Returns:
        str: JSON-like string representation of the schema.
    """
    schema = []
    for column, dtype in df.dtypes.items():
        column_type = str(dtype).upper()
        if column_type == "OBJECT":
          column_type = "STRING"
        elif column_type.startswith("INT"):
          column_type = "INTEGER"
        elif column_type.startswith("FLOAT"):
          column_type = "REAL"
        elif column_type.startswith("DATETIME"):
          column_type = "TIMESTAMP"
        schema.append({
            "name": column,
            "type": column_type,
            "description": ""  # You need to add the description, once the schema is creates as it will be blank when this function is run..you need to enter a description for each of the field/column name
        })
    
    table_data = {
        "table": [
            {
              "table_name": table_name,
              "schema": schema
            }
        ]
    }

    return json.dumps(table_data, indent=2)

# Create a dataframe from your CSV file, and if you have more than one you could loop through them to create one schema json-like string
df = pd.read_csv(your_CSV_file)

# Generate schema string ... "loans" in this case is the table name we want to use in our sqlite db
schema = create_schema_string(df, "loans")
print(schema)