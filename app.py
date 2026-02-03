from decimal import Decimal
from flask import Flask, app, flash, redirect, render_template, request, jsonify, url_for
import traceback as tb
from db import db, init_db
import models as md
import db_utils as dbu
from datetime import time

def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.update(config)

    init_db(app)
    register_routes(app)
    return app


def register_routes(app):
    @app.route('/')
    def home():
        return render_template("home.html")
    
    @app.route("/input_case_work", methods=["GET"])
    def input_case_work():
        users = dbu.get_all_users()
        cases = dbu.get_all_cases()
        return render_template("input_case_work.html",
                            users=users,
                            cases=cases)

    @app.route("/edit-case/<int:case_id>", methods=["GET", "POST"])
    def edit_case(case_id):
        case = db.session.get(md.Case, case_id)
        if not case:
            return jsonify({"message": "Case not found"}), 404

        if request.method == "POST":
            case.name = request.form.get("case-name")
            case.description = request.form.get("case-description")
            case.client_id = int(request.form.get("client-id"))
            case.is_outsourced = "is_outsourced" in request.form

            case.billing_type = md.BillingType(request.form.get("billing_type"))
            case.rate_amount = Decimal(request.form.get("rate_amount", "0.00"))

            db.session.commit()
            return redirect(url_for("case_table"))
        elif request.method == "GET":
            return render_template(
                "edit_case.html",
                case=case,
                clients=dbu.get_all_clients(),
                BillingType=md.BillingType
            )
        else:
            return jsonify({"message": "Method not allowed"}), 405

    @app.route("/edit-case-work/<int:case_work_id>", methods=["GET", "POST"])
    def edit_case_work(case_work_id):
        case_work = db.session.get(md.CaseWork, case_work_id)
        if not case_work:
            return jsonify({"message": "Case work not found"}), 404
        if request.method == "POST":
            case_work.user_id = int(request.form.get("user_id"))
            case_work.case_id = int(request.form.get("case_id"))
            case_work.date = request.form.get("date")
            case_work.start_time = request.form.get("start_time")
            case_work.end_time = request.form.get("end_time")
            case_work.description = request.form.get("description")
            case_work.billed = "billed" in request.form

            db.session.commit()
            return redirect(url_for("case_work_table"))
        elif request.method == "GET":
            return render_template(
                "edit_case_work.html",
                case_work=case_work,
                users=dbu.get_all_users(),
                cases=dbu.get_all_cases())
        else:
            return jsonify({"message": "Method not allowed"}), 405
        
    @app.route("/delete-case-work/<int:case_work_id>")
    def delete_case_work(case_work_id):
        case_work = md.CaseWork.query.get_or_404(case_work_id)

        db.session.delete(case_work)
        db.session.commit()

        flash("A munka sikeresen törölve lett.", "success")
        return redirect(url_for("case_work_table"))
    
    @app.route("/delete-case/<int:case_id>")
    def delete_case(case_id):
        case = md.Case.query.get_or_404(case_id)

        db.session.delete(case)
        db.session.commit()

        flash("Az ügy sikeresen törölve lett.", "success")
        return redirect(url_for("case_table"))

    @app.route("/add-case-work", methods=["POST"])
    def add_case_work_route():
        user_id = request.form.get("user_id")
        case_id = request.form.get("case_id")
        date = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        description = request.form.get("description")

        dbu.create_case_work(user_id, case_id, date, start_time, end_time, description)

        return redirect("/input_case_work")
    
    @app.route("/case-work-table", methods=["GET"])
    def case_work_table():
        case_works = dbu.get_all_case_works()
        return render_template("case_work_table.html", case_works=case_works)

    
    @app.route("/input_case", methods=["GET"])
    def input_case():
        clients = dbu.get_all_clients()

        return render_template("input_case.html", clients=clients, companies=dbu.get_all_outsource_companies())


    @app.route('/get-users', methods=['GET'])
    def get_users():
        try:
            users = md.User.query.all()
            return jsonify([
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email
                } for u in users
            ])
        except Exception as e:
            print(tb.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/get-cases', methods=['GET'])
    def get_cases():
        try:
            cases = md.Case.query.all()
            return jsonify([
                {
                    "id": c.id,
                    "number": c.number,
                    "name": c.name,
                    "client_id": c.client_id,
                    "description": c.description
                } for c in cases
            ])
        except Exception as e:
            print(tb.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/save-case', methods=['POST'])
    def save_case():
        try:
            # Get form data
            data = request.form

            # Create the new Case
            md.Case.create(
                name=data.get('case-name'),
                client_id=int(data.get('client-id')),
                description=data.get('case-description'),
                billing_type=md.BillingType(data.get('billing_type')),
                rate_amount=float(data.get('rate_amount', 0.0)),
                is_outsourced=data.get('is-outsourced') == 'on',
                outsource_company_id=int(data.get('outsource_company_id')) if data.get('is-outsourced') == 'on' else None
            )

            return render_template("input_case.html", message="Sikeresen elmentve!")

        except Exception as e:
            db.session.rollback()
            print(tb.format_exc())
            return render_template("input_case.html", error="Hiba történt az ügy mentésekor.")

    @app.route('/input_outsource_company', methods=['GET', 'POST'])
    def input_outsource_company():
        if request.method == 'POST':
            try:
                name = request.form.get('company-name')
                tax_number = request.form.get('tax-number')

                if not name:
                    return render_template('input_outsource_company.html', error="A név megadása kötelező.")

                # Create the new OutsourceCompany
                new_company = md.OutsourceCompany(name=name, tax_number=tax_number)
                db.session.add(new_company)
                db.session.commit()

                return render_template('input_outsource_company.html', message="Sikeresen hozzáadva!")

            except Exception as e:
                db.session.rollback()
                print(tb.format_exc())
                return render_template('input_outsource_company.html', error="Hiba történt a mentés során.")

        # GET request
        return render_template('input_outsource_company.html')

    @app.route("/case-table", methods=["GET"])
    def case_table():
        cases = dbu.get_all_cases()
        return render_template("case_table.html", cases=cases)
    
    from flask import render_template
    from datetime import date, datetime, timedelta
    from collections import defaultdict
    import calendar
    import db_utils as dbu

    from flask import request
    import calendar
    from datetime import date, datetime, timedelta

    @app.route("/calendar")
    def calendar_view():
        # Get month from query params or use current month
        month_str = request.args.get("month")
        if month_str:
            try:
                current_date = datetime.strptime(month_str, "%Y-%m")
            except ValueError:
                current_date = datetime.today()
        else:
            current_date = datetime.today()

        current_year = current_date.year
        current_month = current_date.month

        # Build month days grid
        first_day = date(current_year, current_month, 1)
        _, num_days = calendar.monthrange(current_year, current_month)

        # Create list of weeks
        month_days = []
        week = []

        # Fill initial empty days
        for _ in range(first_day.weekday() + 1):  # Mon=0..Sun=6
            week.append({"date": None, "works": []})

        for day in range(1, num_days + 1):
            day_date = date(current_year, current_month, day)
            # Fetch works for this day
            works = dbu.get_case_works_by_date(day_date)
            week.append({"date": day_date, "works": works})
            if len(week) == 7:
                month_days.append(week)
                week = []

        # Fill remaining week
        if week:
            while len(week) < 7:
                week.append({"date": None, "works": []})
            month_days.append(week)

        return render_template(
            "calendar.html",
            month_days=month_days,
            current_year=current_year,
            current_month=current_month
        )



    
    @app.route("/client-table", methods=["GET"])
    def client_table():
        # Fetch all clients
        clients = dbu.get_all_clients()
        return render_template("client_table.html", clients=clients)

    @app.route("/input_client", methods=["GET"])
    def input_client():
        return render_template("input_client.html")

    @app.route("/add-client", methods=["POST"])
    def add_client():
        client_type = request.form.get("client_type")
        client_code = request.form.get("client_code")
        name = request.form.get("name")
        tax_number = request.form.get("tax_number")

        if client_type == "PERSON":
            birth_date = request.form.get("birth_date")
            address = request.form.get("address")
            new_client = md.ClientPerson(
                client_code=client_code,
                name=name,
                tax_number=tax_number,
                birth_date=birth_date,
                address=address
            )
        else:
            headquarters = request.form.get("headquarters")
            new_client = md.ClientCompany(
                client_code=client_code,
                name=name,
                tax_number=tax_number,
                headquarters=headquarters
            )

        db.session.add(new_client)
        db.session.commit()
        return redirect("/input_client")