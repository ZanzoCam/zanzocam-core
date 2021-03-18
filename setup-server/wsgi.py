from setup_server import app

if __name__ == "__main__":

    import logging
    logging.basicConfig(filename='error.log',level=logging.DEBUG)

    app.run(host="0.0.0.0", port=8080, debug=False)
