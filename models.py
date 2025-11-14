from db import db

class Case(db.Model):
    __tablename__ = 'cases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(45), nullable=False)
    client_name = db.Column(db.String(45), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Case {self.id}: {self.name}>'