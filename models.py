from db import db
import enum
from sqlalchemy import Enum, Integer, cast, func
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timedelta

class BillingType(enum.Enum):
    HOURLY = "hourly"
    FIXED = "fixed"
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(45), nullable=False, unique=True)
    first_name = db.Column(db.String(45), nullable=True)
    last_name = db.Column(db.String(45), nullable=True)

    # Relationship with CaseWork
    case_works = db.relationship("CaseWork", back_populates="user", lazy=True)

    def __repr__(self):
        return f'<User {self.id}: {self.username}>'

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name
        }

class CaseType(db.Model):
    __tablename__ = 'case_types'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(45), nullable=False, unique=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def __init__(self, name=None, active=True):
        self.name = name
        self.active = active

    def __repr__(self):
        return f'<CaseType {self.id}: {self.name}>'
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "active": self.active,
            "created_at": self.created_at
        }

class Case(db.Model):
    __tablename__ = 'cases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(5), nullable=False, unique=True)
    name = db.Column(db.String(45), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_outsourced = db.Column(db.Boolean, default=False, nullable=False)
    outsource_company_id = db.Column(db.Integer, db.ForeignKey('outsource_companies.id'), nullable=True)
    billing_type = db.Column(Enum(BillingType, values_callable=lambda enum: [e.value for e in enum]), nullable=False,default=BillingType.FIXED)
    rate_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    case_type_id = db.Column(db.Integer, db.ForeignKey('case_types.id'), nullable=True)

    # Relationships
    client = db.relationship("Client", back_populates="cases")
    works = db.relationship("CaseWork", back_populates="case", lazy=True)
    outsource_company = db.relationship("OutsourceCompany", backref="cases", lazy=True)
    case_type = db.relationship("CaseType", backref="cases", lazy=True)

    def __repr__(self):
        return f'<Case {self.number}: {self.name}>'

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "client_id": self.client_id,
            "description": self.description,
            "is_outsourced": self.is_outsourced,
            "outsource_company_id": self.outsource_company_id
        }

    @staticmethod
    def create(name, client_id, description=None, billing_type=BillingType.FIXED, rate_amount=0.00, 
               is_outsourced=False, outsource_company_id=None, case_type_id=None):
        if is_outsourced and not outsource_company_id:
            raise ValueError("Outsource company must be specified for outsourced cases.")

        new_case = Case(
            number="00000",
            name=name,
            client_id=client_id,
            description=description,
            billing_type=billing_type,
            rate_amount=rate_amount,
            is_outsourced=is_outsourced,
            outsource_company_id=outsource_company_id,
            case_type_id=case_type_id
        )

        db.session.add(new_case)
        db.session.flush()

        new_case.number = str(new_case.id).zfill(5)

        if new_case.is_outsourced:
            outsource_company = OutsourceCompany.query.get(outsource_company_id)
            short_name = outsource_company.short_name or ""
            new_case.number = f"{short_name}{new_case.number}"

        db.session.commit()
        return new_case

class OutsourceCompany(db.Model):
    __tablename__ = 'outsource_companies'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    tax_number = db.Column(db.String(20), nullable=True)
    short_name = db.Column(db.String(15), nullable=True)

    def __repr__(self):
        return f'<OutsourceCompany {self.id}: {self.name}>'
    
    def __init__(self, name=None, tax_number=None, short_name=None):
        self.name = name
        self.tax_number = tax_number
        self.short_name = short_name

class CaseWork(db.Model):
    __tablename__ = 'case_work'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    billed = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="case_works")
    case = db.relationship("Case", back_populates="works")
    
    def __repr__(self):
        return f'<CaseWork {self.id} for Case {self.case_id} by User {self.user_id}>'

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "case_id": self.case_id,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "description": self.description,
            "billed": self.billed
        }
    
    @hybrid_property
    def duration_seconds(self):
        if self.start_time and self.end_time:
            start_dt = datetime.combine(self.date, self.start_time)
            end_dt = datetime.combine(self.date, self.end_time)
            return (end_dt - start_dt).total_seconds()
        return 0

    @duration_seconds.expression
    def duration_seconds(cls):
        return (
            cast(func.strftime('%s', cls.end_time), Integer) -
            cast(func.strftime('%s', cls.start_time), Integer)
        )


# ----------------------------
# CLIENTS (polymorphic)
# ----------------------------
class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    client_code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    tax_number = db.Column(db.String(20), nullable=True)
    client_type = db.Column(db.String(20), nullable=False)

    # Polymorphic config
    __mapper_args__ = {
        "polymorphic_on": client_type,
        "polymorphic_identity": "CLIENT",
    }

    # Relationship with cases
    cases = db.relationship("Case", back_populates="client", lazy=True)


class ClientPerson(Client):
    __tablename__ = 'client_persons'

    id = db.Column(db.Integer, db.ForeignKey('clients.id'), primary_key=True)
    birth_date = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(255), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "PERSON",
    }

    def __repr__(self):
        return f'<ClientPerson {self.id}>'


class ClientCompany(Client):
    __tablename__ = 'client_companies'

    id = db.Column(db.Integer, db.ForeignKey('clients.id'), primary_key=True)
    headquarters = db.Column(db.String(255), nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": "COMPANY",
    }

    def __repr__(self):
        return f'<ClientCompany {self.id}>'
