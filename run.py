from app import create_app

app = create_app()

if __name__ == "__main__":
    # O modo Debug é controlado pelo Config que lê o .env
    app.run()
