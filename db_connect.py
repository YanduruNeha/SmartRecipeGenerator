import psycopg2

def get_db_connection():
    try:
        connection = psycopg2.connect(
            dbname="recipe_db",  
            user="postgres",      
            password="root",      
            host="localhost",     
            port="5432"           
        )
        print("Database connection established successfully.")
        return connection
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def get_gpt_key():
    return "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" 

if __name__ == "__main__":
    get_db_connection()
