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
    return "use the key here" 

if __name__ == "__main__":
    get_db_connection()
