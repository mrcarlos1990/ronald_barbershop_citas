from app import app
from ronald_barbershop_citas.seed import seed_database


if __name__ == "__main__":
    with app.app_context():
        seed_database()
        print("Seed completado correctamente.")
