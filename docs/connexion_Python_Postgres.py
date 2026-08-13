import os
import psycopg
from dotenv import load_dotenv

load_dotenv("/home/dymoon/lab/NetAtlas/config/.env")

def connexion_db():
  return psycopg.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
    )  

try:
  connexion = connexion_db()
  print ("Connexion à NetAtlas réussie !")
  connexion.close()
except Exception as erreur:
  print("Error Connexion BDD:",erreur)
