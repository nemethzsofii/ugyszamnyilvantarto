import enum
from sqlalchemy import Enum
from db import db

# ----------------------------
# USERS
# ----------------------------
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


# ----------------------------
# CASES
# ----------------------------
class BillingType(enum.Enum):
    HOURLY = "hourly"
    FIXED = "fixed"

class Case(db.Model):
    __tablename__ = 'cases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(5), nullable=False, unique=True)
    name = db.Column(db.String(45), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_outsourced = db.Column(db.Boolean, default=False, nullable=False)
    billing_type = db.Column(Enum(BillingType, values_callable=lambda enum: [e.value for e in enum]), nullable=False,default=BillingType.FIXED)
    rate_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    # Relationships
    client = db.relationship("Client", back_populates="cases")
    works = db.relationship("CaseWork", back_populates="case", lazy=True)
    allowed_companies = db.relationship(
        "CaseOutsourceMap",
        back_populates="case",
        lazy=True,
        cascade="all, delete-orphan"
    )

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
            "allowed_companies": [map.company_id for map in self.allowed_companies]
        }

    @staticmethod
    def create(name, client_id, description=None, billing_type=BillingType.FIXED, rate_amount=0.00):
        """Create a new Case with a 0-padded number based on the auto-incremented ID."""
        new_case = Case(
            number="00000",
            name=name,
            client_id=client_id,
            description=description,
            billing_type=billing_type,
            rate_amount=rate_amount
        )
        db.session.add(new_case)
        db.session.flush()
        new_case.number = str(new_case.id).zfill(5)
        db.session.commit()
        return new_case

class OutsourceCompany(db.Model):
    __tablename__ = 'outsource_companies'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    tax_number = db.Column(db.String(20), nullable=True)

    # Relationship for cases it’s allowed to work on
    cases_allowed = db.relationship(
        "CaseOutsourceMap",
        back_populates="company",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f'<OutsourceCompany {self.id}: {self.name}>'


class CaseOutsourceMap(db.Model):
    __tablename__ = 'case_outsource_map'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('outsource_companies.id'), nullable=False)

    case = db.relationship("Case", back_populates="allowed_companies")
    company = db.relationship("OutsourceCompany", back_populates="cases_allowed")

    def __repr__(self):
        return f'<CaseOutsourceMap Case {self.case_id} ↔ Company {self.company_id}>'

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
