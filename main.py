from flask import Flask, render_template, request, jsonify
import traceback as tb
from db import db, init_db
import models as md

def create_app(config=None):
    app = Flask(__name__)
    
    # Load config
    if config:
        app.config.update(config)
    
    # Initialize DB
    init_db(app)
    
    # Register routes
    register_routes(app)
    
    return app

def register_routes(app):
    @app.route('/')
    def hello_world():
        return render_template("data_input.html")

    @app.route('/add-case', methods=['POST'])
    def add_case():
        try:
            data = request.form
            case_number = data.get('case-number')
            case_name = data.get('case-name')
            client_name = data.get('client-name')
            case_description = data.get('case-description')
            
            new_case = md.Case(
                name=case_name,
                client_name=client_name,
                description=case_description
            )
            db.session.add(new_case)
            db.session.commit()
            return jsonify({"message": "Case added successfully!"}), 200
        except Exception as e:
            db.session.rollback()
            print(f"Error adding case: {tb.format_exc()}")
            return jsonify({"error": f"Error adding case: {str(e)}"}), 500

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)