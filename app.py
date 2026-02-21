from decimal import Decimal
import os
from pydoc import doc
import secrets
from flask import Flask, app, flash, redirect, render_template, request, jsonify, url_for, Blueprint, send_file, abort
import traceback as tb
from datetime import date, datetime
import calendar
import tempfile
import webbrowser

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import pagesizes
from reportlab.lib.units import inch
from datetime import timedelta

from sqlalchemy import case, func, text

import db_utils as dbu
from db import db, init_db
import models as md

import general_utils as gu

def create_app(config=None):
    app = Flask(__name__)

    if config:
        app.config.update(config)
    app.config["SECRET_KEY"] = get_or_create_secret_key()

    init_db(app)
    register_routes(app)

    @app.errorhandler(Exception)
    def handle_error(e):
        # Default values
        error_code = getattr(e, 'code', 500)
        error_message = getattr(e, 'description', 'Something went wrong!')

        # handle custom messages for certain errors
        if error_code == 404:
            error_message = "Page not found!"
        elif error_code == 500:
            error_message = "Internal server error!"
        elif error_code == 405:
            error_message = "Method not allowed!"
        elif error_code == 400:
            error_message = "Bad request!"
        print(tb.format_exc())

        return render_template(
            "error.html",
            error_code=error_code,
            error_message=error_message
        ), error_code
    
    return app

def get_or_create_secret_key():
    key_file = "static/files/secret_key.txt"

    if os.path.exists(key_file):
        with open(key_file, "r") as f:
            return f.read().strip()
    else:
        key = secrets.token_hex(32)
        with open(key_file, "w") as f:
            f.write(key)
        return key
    
def register_routes(app):
    @app.route('/')
    def home():
        return render_template("home.html")

    @app.route("/cases/<case_number>/export-pdf")
    def export_case_pdf(case_number):
        # ---- Fetch Case ----
        case = md.Case.query.filter_by(number=case_number).first()

        if not case:
            return jsonify({"error": "Ügy nem található."}), 404

        # ---- Fetch Works ----
        works = (
            md.CaseWork.query
            .filter_by(case_id=case.id, billed=False)
            .order_by(md.CaseWork.date, md.CaseWork.start_time)
            .all()
        )

        if not works:
            return jsonify({"error": "Nem található rögzített munka ehhez az ügyhöz."}), 404

        # ---- PDF Setup ----
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesizes.A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20
        )

        # Define a style for wrapping text in the table
        table_style = ParagraphStyle(
            name="TableCell",
            fontName="Helvetica",
            fontSize=8,
            leading=10,            # line height
            alignment=TA_LEFT
        )

        elements = []
        styles = getSampleStyleSheet()

        # ---- Title ----
        elements.append(
            Paragraph(
                f"<b>Ügy összefoglaló</b><br/>{case.number} - {case.name}",
                styles["Heading1"]
            )
        )
        elements.append(Spacer(1, 0.4 * inch))

        # ---- Table Header ----
        data = [[
            "Dátum",
            "Felhasználó",
            "Kezdet",
            "Vége",
            "Idotartam (h)",
            "Leírás"
        ]]

        total_seconds = 0

        # ---- Table Rows ----
        for w in works:
            duration_hours = round(w.duration_seconds / 3600, 2)
            total_seconds += w.duration_seconds

            row = [
                Paragraph(w.date.strftime("%Y-%m-%d"), table_style),
                Paragraph(w.user.username if w.user else "-", table_style),
                Paragraph(w.start_time.strftime("%H:%M"), table_style),
                Paragraph(w.end_time.strftime("%H:%M"), table_style),
                Paragraph(f"{duration_hours}", table_style),
                Paragraph("Yes" if w.billed else "No", table_style),
                Paragraph(w.description.replace("ő", "o") or "-", table_style)
            ]
            data.append(row)

        total_hours = round(total_seconds / 3600, 2)

        # ---- Create Table ----
        table = Table(
            data,
            repeatRows=1,
            colWidths = [60, 90, 40, 40, 60, 40, 225],
            splitByRow=1  # allows row to break over pages
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),

            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),

            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.whitesmoke,
                colors.transparent
            ])
        ]))

        elements.append(table)
        elements.append(Spacer(1, 0.4 * inch))

        # ---- Total Summary ----
        elements.append(
            Paragraph(
                f"<b>Total hours:</b> {total_hours} h",
                styles["Heading2"]
            )
        )

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Save to temp file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, f"case_{case.number}_report.pdf")

        with open(file_path, "wb") as f:
            f.write(buffer.read())

        # Open with default system PDF viewer
        webbrowser.open(file_path)

        return jsonify({"success": True})

    @app.route("/reports")
    def reports():
        active_only = request.args.get("active_only", "1") == "1"  # default checked

        # -----------------------------
        # 1. Total worked hours per case
        # -----------------------------
        query1 = (
            db.session.query(
                md.Case.id.label("case_id"),
                md.Case.number.label("case_number"),
                md.Case.name.label("case_name"),
                md.Client.name.label("client_name"),
                (func.sum(md.CaseWork.duration_seconds) / 3600).label("total_hours")
            )
            .join(md.CaseWork)
            .join(md.Client)
        )

        if active_only:
            query1 = query1.filter(md.Case.is_active == True)

        results1 = query1.group_by(md.Case.id, md.Client.name).order_by(md.Case.number).all()

        # -----------------------------
        # 2. Work per user
        # -----------------------------
        query2 = (
            db.session.query(
                md.User.username,
                func.sum(md.CaseWork.duration_seconds).label("total_seconds")
            )
            .join(md.CaseWork)
        )

        if active_only:
            query2 = query2.join(md.Case).filter(md.Case.is_active == True)

        results2 = query2.group_by(md.User.username).order_by(
            func.sum(func.strftime('%s', md.CaseWork.end_time) -
                    func.strftime('%s', md.CaseWork.start_time)).desc()
        ).all()

        # -----------------------------
        # 3. UNBILLED WORK PER CASE
        # -----------------------------
        query3 = (
            db.session.query(
                md.Case.number.label("case_number"),
                md.Case.name.label("case_name"),
                md.Client.name.label("client_name"),
                (func.sum(md.CaseWork.duration_seconds) / 3600).label("unbilled_hours"),
                case(
                    (md.Case.billing_type == "hourly",
                    (func.sum(md.CaseWork.duration_seconds) / 3600) * md.Case.rate_amount),
                    else_=md.Case.rate_amount
                ).label("estimated_amount")
            )
            .join(md.CaseWork)
            .join(md.Client)
            .filter(md.CaseWork.billed == False)
        )

        if active_only:
            query3 = query3.filter(md.Case.is_active == True)

        unbilled = query3.group_by(md.Case.id, md.Client.name).order_by(md.Case.number).all()

        return render_template(
            "reports.html",
            reports1=results1,
            reports2=results2,
            unbilled=unbilled,
            active_only=active_only
        )

    @app.route("/edit-outsource-company/<int:company_id>", methods=["GET", "POST"])
    def edit_outsource_company(company_id):
        company = db.session.get(md.OutsourceCompany, company_id)
        if not company:
            return jsonify({"message": "Company not found"}), 404

        if request.method == "POST":
            company.name = request.form.get("company-name")
            company.short_name = request.form.get("company-short-name")
            company.tax_number = request.form.get("company-tax-number")

            db.session.commit()
            return redirect(url_for("outsource_company_table"))
        elif request.method == "GET":
            return render_template(
                "edit_outsource_company.html",
                company=company
            )
        else:
            return jsonify({"message": "Method not allowed"}), 405
    
    @app.route("/edit-client/<int:client_id>", methods=["GET", "POST"])
    def edit_client(client_id):
        client = db.session.get(md.Client, client_id)
        if not client:
            return jsonify({"message": "Client not found"}), 404

        if request.method == "POST":
            client.name = request.form.get("client-name")
            client.client_code = request.form.get("client-client-code")
            client.tax_number = request.form.get("client-tax-number")
            if isinstance(client, md.ClientPerson):
                client.birth_date = request.form.get("client-birth-date")
                client.address = request.form.get("client-address")
            elif isinstance(client, md.ClientCompany):
                client.headquarters = request.form.get("client-headquarters")

            db.session.commit()
            return redirect(url_for("client_table"))
        elif request.method == "GET":
            return render_template(
                "edit_client.html",
                client=client
            )
        else:
            return jsonify({"message": "Method not allowed"}), 405

    @app.route("/delete-outsource-company/<int:company_id>", methods=["POST"])
    def delete_outsource_company(company_id):
        try:
            company = md.OutsourceCompany.query.get_or_404(company_id)

            db.session.delete(company)
            db.session.commit()

            flash("A bedolgozó cég sikeresen törölve lett.", "success")
            return redirect(url_for("outsource_company_table"))
        except Exception as e:
            db.session.rollback()
            print(tb.format_exc())
            flash("Hiba történt a bedolgozó cég törlésekor.", "danger")
            return redirect(url_for("outsource_company_table"))
    
    @app.route("/delete-client/<int:client_id>", methods=["POST"])
    def delete_client(client_id):
        try:
            client = md.Client.query.get_or_404(client_id)

            db.session.delete(client)
            db.session.commit()

            flash("Az ügyfél sikeresen törölve lett.", "success")
            return redirect(url_for("client_table"))
        except Exception as e:
            db.session.rollback()
            print(tb.format_exc())
            flash("Hiba történt az ügyfél törlésekor.", "danger")
            return redirect(url_for("client_table"))
    
    @app.route("/delete-user/<int:user_id>", methods=["POST"])
    def delete_user(user_id):
        try:
            user = md.User.query.get_or_404(user_id)

            db.session.delete(user)
            db.session.commit()

            flash("A felhasználó sikeresen törölve lett.", "success")
            return redirect(url_for("user_table"))
        except Exception as e:
            db.session.rollback()
            print(tb.format_exc())
            flash("Hiba történt a felhasználó törlésekor.", "danger")
            return redirect(url_for("user_table"))

    @app.route("/input_case_work", methods=["GET", "POST"])
    def input_case_work():
        users = dbu.get_all_users()
        cases = dbu.get_all_cases()
        if request.method == "POST":
            try:
                user_id = int(request.form.get("user_id"))
                case_id = int(request.form.get("case_id"))
                description = request.form.get("description")

                # Parse date and time fields
                date_str = request.form.get("date")
                date_obj = None
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                start_time_str = request.form.get("start_time")
                end_time_str = request.form.get("end_time")
                start_time = None
                end_time = None
                if start_time_str:
                    start_time = gu.parse_time(start_time_str)
                if end_time_str:
                    end_time = gu.parse_time(end_time_str)

                if not all([user_id, case_id, date_obj, start_time, end_time]):
                    return render_template("input_case_work.html",
                                        users=users,
                                        cases=cases,
                                        error="Minden mező kitöltése kötelező!")

                # create case work object and save to database
                dbu.create_case_work(user_id, case_id, date_obj, start_time, end_time, description)

                return render_template("input_case_work.html",
                                    users=users,
                                    cases=cases,
                                    message="Munkalap sikeresen elmentve!")
            except Exception as e:
                print(tb.format_exc())
                return render_template("input_case_work.html",
                                    users=users,
                                    cases=cases,
                                    error="Hiba történt a munkalap mentésekor.")
        # GET request
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
            case.number = request.form.get("case-number")
            case.description = request.form.get("case-description")
            case.client_id = int(request.form.get("client-id"))
            case.case_type_id = int(request.form.get("case-type-id")) if request.form.get("case-type-id") else None

            case.billing_type = md.BillingType(request.form.get("billing_type"))
            case.rate_amount = Decimal(request.form.get("rate_amount", "0.00"))

            case.is_active = "is-active" in request.form

            db.session.commit()
            return redirect(url_for("case_table"))
        elif request.method == "GET":
            return render_template(
                "edit_case.html",
                case=case,
                clients=dbu.get_all_clients(),
                case_types=dbu.get_all_case_types(),
                companies=dbu.get_all_outsource_companies(),
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
            user_id = int(request.form.get("user_id"))
            case_id = int(request.form.get("case_id"))
            description = request.form.get("description")
            # Parse date and time fields
            date_str = request.form.get("date")
            date_obj = None
            if date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time_str = request.form.get("start_time")
            end_time_str = request.form.get("end_time")
            start_time = None
            end_time = None
            if start_time_str:
                start_time = gu.parse_time(start_time_str)
            if end_time_str:
                end_time = gu.parse_time(end_time_str)
            if not all([user_id, case_id, date_obj, start_time, end_time]):
                return render_template("edit_case_work.html",
                                    case_work=case_work,
                                    users=dbu.get_all_users(),
                                    cases=dbu.get_all_cases(),
                                    error="Minden mező (kivéve a leírást) kitöltése kötelező!")
            
            case_work.user_id = user_id
            case_work.case_id = case_id
            case_work.date = date_obj
            case_work.start_time = start_time
            case_work.end_time = end_time
            case_work.description = description
            case_work.billed = "billed" in request.form

            db.session.commit()
            return redirect(url_for("case_work_table"))
        elif request.method == "GET":
            print(dbu.get_all_users())
            return render_template(
                "edit_case_work.html",
                case_work=case_work,
                users=dbu.get_all_users(),
                cases=dbu.get_all_cases())
        else:
            return jsonify({"message": "Method not allowed"}), 405
    
    @app.route("/edit-user/<int:user_id>", methods=["GET", "POST"])
    def edit_user(user_id):
        user = db.session.get(md.User, user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404
        if request.method == "POST":
            if dbu.get_user_by_username(request.form.get("username")) and dbu.get_user_by_username(request.form.get("username")).id != user_id:
                return render_template("edit_user.html", user=user, error="Ez a felhasználónév már foglalt.")
            user.username = request.form.get("username")
            user.first_name = request.form.get("first_name")
            user.last_name = request.form.get("last_name")

            db.session.commit()
            return redirect(url_for("user_table"))
        elif request.method == "GET":
            return render_template(
                "edit_user.html",
                user=user)
        else:
            return jsonify({"message": "Method not allowed"}), 405
        
    @app.route("/delete-case-work/<int:case_work_id>", methods=["POST"])
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
    
    @app.route("/case-work-table", methods=["GET"])
    def case_work_table():
        case_works = dbu.get_all_case_works()
        return render_template("case_work_table.html", case_works=case_works)
    
    @app.route("/user-table", methods=["GET"])
    def user_table():
        users = dbu.get_all_users()
        return render_template("user_table.html", users=users)
    
    @app.route("/input_case", methods=["GET", "POST"])
    def input_case():
        clients = dbu.get_all_clients()
        if request.method == "POST":
            try:
                # Get form data
                data = request.form
                case_name = data.get('case-name')
                client_id = data.get('client-id')
                billing_type = data.get('billing_type')
                rate_amount = data.get('rate_amount')
                if not case_name or not client_id or not billing_type and not rate_amount:
                    return render_template("input_case.html", clients=clients,
                                           companies=dbu.get_all_outsource_companies(),
                                            case_types=dbu.get_all_case_types(),
                                            error="Az ügy neve, az ügyfél, a díjazás típusa és a díj mértéke kiválasztása kötelező.")

                # Create the new Case
                md.Case.create(
                    name=case_name,
                    client_id=client_id,
                    description=data.get('case-description'),
                    billing_type=md.BillingType(billing_type),
                    rate_amount=float(rate_amount) if rate_amount else 0.0,
                    is_outsourced=data.get('is-outsourced') == 'on',
                    outsource_company_id=int(data.get('outsource_company_id')) if data.get('is-outsourced') == 'on' else None,
                    case_type_id=int(data.get('case_type_id')) if data.get('case_type_id') else None
                )
                return render_template("input_case.html", clients=clients,
                                       companies=dbu.get_all_outsource_companies(),
                                        case_types=dbu.get_all_case_types(),
                                        message="Sikeresen hozzáadva!")
            except Exception as e:
                print(tb.format_exc())
                return render_template("input_case.html", clients=clients,
                                       companies=dbu.get_all_outsource_companies(),
                                       case_types=dbu.get_all_case_types(),
                                       error="Hiba történt az ügy felvételénél.")

        # GET request
        return render_template("input_case.html", clients=clients,
                               companies=dbu.get_all_outsource_companies(),
                               case_types=dbu.get_all_case_types())

    @app.route('/input_user', methods=['GET', 'POST'])
    def input_user():
        if request.method == 'POST':
            try:
                username = request.form.get('username')
                first_name = request.form.get('first_name')
                last_name = request.form.get('last_name')

                if not username:
                    return render_template('input_user.html', error="A felhasználónév megadása kötelező.")
                if not first_name:
                    return render_template('input_user.html', error="A vezetéknév megadása kötelező.")
                if not last_name:
                    return render_template('input_user.html', error="A keresztnév megadása kötelező.")
                if dbu.get_user_by_username(username):
                    return render_template('input_user.html', error="Ez a felhasználónév már foglalt.")
                new_user = md.User(username=username, first_name=first_name, last_name=last_name)
                db.session.add(new_user)
                db.session.commit()

                return render_template('input_user.html', message="Sikeresen hozzáadva!")

            except Exception as e:
                db.session.rollback()
                print(tb.format_exc())
                return render_template('input_user.html', error="Hiba történt a mentés során.")

        # GET request
        return render_template('input_user.html')
    
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

    @app.route('/input_outsource_company', methods=['GET', 'POST'])
    def input_outsource_company():
        if request.method == 'POST':
            try:
                name = request.form.get('company-name')
                tax_number = request.form.get('tax-number')
                short_name = request.form.get('company-short-name')

                if not name:
                    return render_template('input_outsource_company.html', error="A név megadása kötelező.")
                if not short_name:
                    return render_template('input_outsource_company.html', error="A rövid név megadása kötelező.")
                if tax_number and len(tax_number) != 11:
                    return render_template('input_outsource_company.html', error="Az adószámnak 11 karakterből kell állnia.")
                # Create the new OutsourceCompany
                new_company = md.OutsourceCompany(name=name, tax_number=tax_number, short_name=short_name)
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
    
    @app.route("/outsource-company-table", methods=["GET"])
    def outsource_company_table():
        companies = dbu.get_all_outsource_companies()
        return render_template("outsource_company_table.html", outsource_companies=companies)

    @app.route("/calendar")
    def calendar_view():
        # Get month from query params or use current month
        month_str = request.args.get("month")
        try:
            current_date = datetime.strptime(month_str, "%Y-%m") if month_str else datetime.today()
        except ValueError:
            current_date = datetime.today()

        current_year = current_date.year
        current_month = current_date.month

        # Build month days grid using calendar.Calendar (Monday-first)
        cal = calendar.Calendar(firstweekday=0)  # 0 = Monday
        month_days = []

        for week in cal.monthdatescalendar(current_year, current_month):
            week_list = []
            for day_date in week:
                if day_date.month == current_month:
                    works = dbu.get_case_works_by_date(day_date)
                    week_list.append({"date": day_date, "works": works})
                else:
                    week_list.append({"date": None, "works": []})
            month_days.append(week_list)

        today = date.today()
        return render_template(
            "calendar.html",
            month_days=month_days,
            current_year=current_year,
            current_month=current_month,
            today=today
        )

    
    @app.route("/client-table", methods=["GET"])
    def client_table():
        # Fetch all clients
        clients = dbu.get_all_clients()
        return render_template("client_table.html", clients=clients)

    @app.route('/input_client', methods=['GET', 'POST'])
    def input_client():
        if request.method == 'POST':
            try:
                client_type = request.form.get("client_type")
                client_code = request.form.get("client_code")
                name = request.form.get("name")
                tax_number = request.form.get("tax_number")
                if not client_type:
                    return render_template('input_client.html', error="Az ügyféltípus megadása kötelező.")
                if not name:
                    return render_template('input_client.html', error="A név megadása kötelező.")
                if tax_number and len(tax_number) != 11:
                    return render_template('input_client.html', error="Az adószámnak 11 karakterből kell állnia.")

                if client_type == "PERSON":
                    birth_date = request.form.get("birth_date")
                    address = request.form.get("address")
                    new_client = md.ClientPerson(
                        client_code=client_code,
                        name=name,
                        tax_number=tax_number,
                        birth_date=datetime.strptime(birth_date, "%Y-%m-%d") if birth_date else None,
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
                return render_template('input_client.html', message="Sikeresen hozzáadva!")

            except Exception as e:
                db.session.rollback()
                print(tb.format_exc())
                return render_template('input_client.html', error="Hiba történt a mentés során.")

        # GET request
        return render_template('input_client.html')