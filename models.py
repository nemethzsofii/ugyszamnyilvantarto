from db import db

class Case(db.Model):
    __tablename__ = 'cases'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    number = db.Column(db.String(45), nullable=False)
    name = db.Column(db.String(45), nullable=False)
    client_name = db.Column(db.String(45), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Case {self.number}: {self.name}>'
    
    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "name": self.name,
            "client_name": self.client_name,
            "description": self.description
        }