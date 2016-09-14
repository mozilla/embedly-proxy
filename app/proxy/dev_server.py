from app import create_app

if __name__ == '__main__':  # pragma: no cover
    app = create_app()
    app.run(host='0.0.0.0', port=7001, debug=True)
